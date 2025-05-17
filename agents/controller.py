import anthropic
import os
from typing import List, Dict, Any
import json
from agents.prompt import controller_system_prompt
from dotenv import load_dotenv
from agents.data_retriever import BitqueryDataRetriever
from agents.config import get_model_config, ModelConfig
from agents.visualizer import VisualizerAgent
from datetime import datetime
import uuid

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
                    "description": "The visualization requirements"
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
    }
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
            return {
                "tool_name": tool_name,
                "result": result
            }
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

def process_with_claude(user_message: str, max_turns: int = 5) -> List[Dict[str, Any]]:
    """
    Process user message with Claude API using defined tools
    
    Returns:
        List[Dict[str, Any]]: List of conversation messages including tool calls and results
    """
    messages = [{"role": "user", "content": user_message}]
    current_turn = 0
    conversation_history = []
    
    while current_turn < max_turns:
        print(f"\nTurn {current_turn + 1}:")
        try:
            # Get response from Claude
            response = client.messages.create(
                model=get_model_config(ModelConfig.SONNET)["model_name"],
                max_tokens=1024,
                messages=messages,
                system=controller_system_prompt,
                tools=tools
            )
            
            # Add Claude's response to conversation history
            if hasattr(response, "content") and isinstance(response.content, list):
                assistant_message = " ".join([c.text for c in response.content if c.type == "text"])
                conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
            else:
                conversation_history.append({
                    "role": "assistant",
                    "content": str(response.content)
                })
            
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
                
                # Add tool call and result to conversation history
                conversation_history.append({
                    "role": "tool",
                    "name": tool_call["name"],
                    "content": result["result"]
                })
            
            # Add tool results to messages
            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": str(response.content)}] if isinstance(response.content, list) else str(response.content)
            })
            
            # Convert tool results to JSON string before adding to messages
            tool_results_message = json.dumps({"tool_results": tool_results})
            messages.append({
                "role": "user",
                "content": tool_results_message
            })
            
            # Print tool results
            print("\nTool execution results:")
            print(tool_results_message)
            
            current_turn += 1
            
        except Exception as e:
            print(f"Error in turn {current_turn + 1}: {str(e)}")
            conversation_history.append({
                "role": "error",
                "content": f"Error occurred: {str(e)}"
            })
            return conversation_history
    
    print(conversation_history)
    return conversation_history
