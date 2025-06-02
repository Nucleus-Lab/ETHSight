import anthropic
import os
from typing import List, Dict, Any
import json
from agents.prompt import controller_system_prompt
from dotenv import load_dotenv
from agents.data_retriever import BitqueryDataRetriever
from agents.config import get_model_config, ModelConfig
from agents.visualizer import VisualizerAgent
from agents.data_processor import DataProcessor
from datetime import datetime
import uuid
from agents.utils import CMCAPI

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=api_key)

# Initialize agents
data_retriever = BitqueryDataRetriever()
visualizer = VisualizerAgent()
data_processor = DataProcessor()

# Define tools
tools = [
    {
        "name": "get_data",
        "description": "Retrieve data based on user query",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The GraphQL query to retrieve data."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "visualize",
        "description": "Create visualization based on user query and data",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The visualization request specifying what metrics and data to plot. Should align with the user's current prompt and conversation context, considering the CSV file structure."
                },
                "task": {
                    "type": "string",
                    "description": "The current task split from the user's prompt"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the data file"
                }
            },
            "required": ["query", "task", "file_path"]
        }
    },
    {
        "name": "process_data",
        "description": "Process and transform data using Python code",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the input CSV file"
                },
                "prompt": {
                    "type": "string",
                    "description": "Description of how to process the data"
                }
            },
            "required": ["file_path", "prompt"]
        }
    },
    # {
    #     "name": "get_cmc_ohlcv",
    #     "description": "Get historical OHLCV data from CoinMarketCap",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "symbol": {
    #                 "type": "string",
    #                 "description": "Alternatively pass one or more comma-separated cryptocurrency symbols. Example: 'BTC,ETH'"
    #             },
    #             "time_period": {
    #                 "type": "string",
    #                 "description": "Time period to return OHLCV data for. Options: 'daily', 'hourly'",
    #                 "default": "daily"
    #             },
    #             "time_start": {
    #                 "type": "string",
    #                 "description": "Start time in ISO format (e.g., '2025-05-11T00:00:00.000Z')"
    #             },
    #             "time_end": {
    #                 "type": "string",
    #                 "description": "End time in ISO format (e.g., '2025-05-18T00:00:00.000Z')"
    #             },
    #             "count": {
    #                 "type": "integer",
    #                 "description": "Limit the number of time periods to return. Defaults to 10, max 10000",
    #                 "default": 10
    #             },
    #             "interval": {
    #                 "type": "string",
    #                 "description": "Adjust the interval that time_period is sampled. Options: Hours: '1h', '2h', '3h', '4h', '6h', '12h'; Days: '1d', '2d', '3d', '7d', '14d', '15d', '30d', '60d', '90d', '365d'; Other: 'hourly', 'daily', 'weekly', 'monthly', 'yearly'",
    #                 "default": "daily"
    #             },
    #             "convert": {
    #                 "type": "string",
    #                 "description": "Currency to convert to",
    #                 "default": "USD"
    #             }
    #         },
    #         "required": ["symbol", "time_start", "time_end", "interval"]
    #     }
    # }
]

def process_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process tool calls from Claude's response
    """
    tool_calls = []
    if hasattr(message, "content") and isinstance(message.content, list):
        for content in message.content:
            if content.type == "tool_use":
                # content.input is already a dict, no need to parse
                tool_calls.append({
                    "name": content.name,
                    "arguments": content.input
                })
    return tool_calls

def execute_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the specified tool and return its result
    """
    try:
        tool_name = tool_call["name"]
        args = tool_call["arguments"]
        
        if tool_name == "get_data":
            # Use BitqueryDataRetriever to get data
            result = data_retriever.get_data(args["query"])
            if result is not None:
                return {
                    "tool_name": tool_name,
                    "result": result
                }
            else:
                return {
                    "tool_name": tool_name,
                    "result": "Failed to retrieve data"
                }
        elif tool_name == "visualize":
            # Generate a unique output path for the visualization
            output_path = f"data/visualization_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4()}.png"
            result = visualizer.visualize_by_prompt(
                prompt=args["query"],
                task=args["task"],
                file_path=args["file_path"],
                output_png_path=output_path
            )
            signal_list = visualizer.identify_signal(args["query"], args["file_path"])
            return {
                "tool_name": tool_name,
                "result": {
                    "visualization_result": result,
                    "signal_list": signal_list
                }
            }
        elif tool_name == "process_data":
            # Process data using DataProcessor
            result = data_processor.process_with_code(
                file_path=args["file_path"],
                prompt=args["prompt"]
            )
            if result is not None:
                return {
                    "tool_name": tool_name,
                    "result": result
                }
            else:
                return {
                    "tool_name": tool_name,
                    "result": "Failed to process data"
                }
        # elif tool_name == "get_cmc_ohlcv":
        #     api_key = os.getenv("CMC_API_KEY")
        #     if not api_key:
        #         return {
        #             "tool_name": tool_name,
        #             "result": "CMC_API_KEY not found in environment variables"
        #         }
        #     cmc = CMCAPI(api_key=api_key)
        #     df = cmc.get_ohlcv(
        #         symbol=args["symbol"],
        #         time_period=args.get("time_period", "daily"),
        #         time_start=args.get("time_start"),
        #         time_end=args.get("time_end"),
        #         count=args.get("count", 10),
        #         interval=args.get("interval", "daily"),
        #         convert=args.get("convert", "USD")
        #     )
        #     if df is not None and not df.empty:
        #         # Generate a unique filename
        #         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        #         file_id = str(uuid.uuid4())
        #         file_path = f"data/cmc_data/cmc_{args['symbol']}_{args.get('interval', '1d')}_{timestamp}_{file_id}.csv"
                
        #         # Save to CSV
        #         df.to_csv(file_path)
                
        #         return {
        #             "tool_name": tool_name,
        #             "result": {
        #                 "file_path": file_path,
        #                 "df_head": df.head().to_string(),
        #                 "description": f"CMC historical OHLCV data for {args['symbol']} with {args.get('interval', '1d')} interval"
        #             }
        #         }
        #     else:
        #         return {
        #             "tool_name": tool_name,
        #             "result": "No data returned from CMC for the given parameters."
        #         }
        else:
            return {
                "tool_name": tool_name,
                "result": f"Unknown tool: {tool_name}"
            }
    except Exception as e:
        return {
            "tool_name": tool_call.get("name", "unknown"),
            "result": f"Error executing tool: {str(e)}"
        }

def process_with_claude(conversation_history: List[Dict[str, Any]], max_turns: int = 5) -> List[Dict[str, Any]]:
    """
    Process user message with Claude API using defined tools
    
    Args:
        conversation_history: Complete conversation history
        max_turns: Maximum number of turns for the conversation
        
    Returns:
        List[Dict[str, Any]]: Latest messages for this turn
    """
    current_turn = 0
    latest_messages = []  # Store only the latest messages for this turn
    
    while current_turn < max_turns:
        print(f"\nTurn {current_turn + 1}:")
        try:
            # Get response from Claude using full conversation history
            response = client.messages.create(
                model=get_model_config(ModelConfig.SONNET)["model_name"],
                max_tokens=1024,
                messages=conversation_history,  # Use full history
                system=controller_system_prompt + f'\n\nCurrent time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                tools=tools
            )
            
            # Add Claude's response to both conversation history and latest messages
            if hasattr(response, "content") and isinstance(response.content, list):
                assistant_message = " ".join([c.text for c in response.content if c.type == "text"])
                message = {
                    "role": "assistant",
                    "content": assistant_message
                }
            else:
                message = {
                    "role": "assistant",
                    "content": str(response.content)
                }
            
            conversation_history.append(message)
            latest_messages.append(message)
            
            # Print Claude's response
            print("\nClaude's response:")
            if hasattr(response, "content") and isinstance(response.content, list):
                for content in response.content:
                    if content.type == "text":
                        print(content.text)
            else:
                print(response.content)
            
            # Process tool calls if any
            tool_calls = process_tool_calls(response)
            print(tool_calls)
            
            if not tool_calls:
                # If no tool calls, this is the final response
                break
            
            # Execute tools and collect results
            tool_results = []
            for tool_call in tool_calls:
                print(f"\nExecuting tool: {tool_call['name']}")
                result = execute_tool(tool_call)
                tool_results.append(result)
                print(f"Tool result: {result['result']}")
                
                # Add tool call and result to both conversation history and latest messages
                tool_message = {
                    "role": "tool",
                    "name": tool_call["name"],
                    "content": result["result"]
                }
                latest_messages.append(tool_message)
            
            # Add tool results to conversation history
            tool_results_message = json.dumps({"tool_results": tool_results})
            user_message = {
                "role": "user",
                "content": tool_results_message
            }
            conversation_history.append(user_message)
            
            # Print tool results
            print("\nTool execution results:")
            print(tool_results_message)
            
            current_turn += 1
            
        except Exception as e:
            print(f"Error in turn {current_turn + 1}: {str(e)}")
            error_message = {
                "role": "error",
                "content": f"Error occurred: {str(e)}"
            }
            conversation_history.append(error_message)
            latest_messages.append(error_message)
            return latest_messages
    
    print("\nLatest messages for this turn:")
    print(latest_messages)
    return latest_messages
