import dspy
import pandas as pd
import re
from typing import List, Dict
from io import StringIO
import json
from pydantic import BaseModel

class Signal(BaseModel):
    signal_name: str
    signal_description: str

class Visualizer(dspy.Signature):
    """
    You are a visualization expert in python plotly. 
    You are given a user's prompt and a CSV data file. 
    You need to plot the data in the CSV file using python plotly. 
    Read the data from the CSV file and plot the data using python plotly. 
    Remember, do not directly use the sample data of the CSV file, you need to read the data from the CSV file. 
    Do not assume what the data is, always read the data from the CSV file. You can refer to sample data for the structure of the data.
    
    Rules:
    1. Always check what data is available in the CSV file. The sample data is given to you.
    2. Only use columns that are available in the data! Avoid keyerror! Strictly follow the column names in the sample data.
    3. When u plot wallet address or contract address, only show the first 4 and last 4 characters, with ellipsis in the middle because they are too long.
    4. No need to use fig.show() in the plot code, just return the plot code.
    5. If the data is token balances or similar, you should get the decimals of the contract from the data and then convert the balance to the token's decimal so that the visualization scale is easier to understand.
    6. If there are timestamp data in the CSV data and you want to use it, you should convert the timestamp to a human readable date and time, remember to use unit='s' when converting the timestamp to a datetime object.
    7. Use encoding='utf-8' when reading the CSV file.
    8. Cannot accept list of column references or list of columns for both `x` and `y` in the plot code.
    9. Depending on the data, you can also use tables to visualize the data if it is suitable.
    """

    prompt = dspy.InputField(prefix="User's prompt:")
    task = dspy.InputField(prefix="The current task split from the user's prompt:")
    file_path = dspy.InputField(prefix="The file path of the CSV data:")
    sample_data = dspy.InputField(prefix="The sample data of the CSV file:")
    reasoning = dspy.OutputField(
        prefix="Which information should be visualized based on the user's prompt?"
    )
    plot_code: str = dspy.OutputField(prefix="The plot python plotly code:")

class SignalIdentifier(dspy.Signature):
    """
    You are a signal identifier in python.
    You are given a user's prompt and sample data of a CSV file.
    You need to identify the signal in the data.
    A signal is a piece of indicator that might be useful for user to trade.
    """
    prompt = dspy.InputField(prefix="User's prompt:")
    sample_data = dspy.InputField(prefix="The sample data of the CSV file:")
    signal_list: list[Signal] = dspy.OutputField(prefix="The signal in the data:")

class VisualizerAgent:
    def __init__(self, engine=None) -> None:
        self.engine = engine
        self.visualize = dspy.Predict(Visualizer, max_tokens=16000)
        self.signal_identifier = dspy.Predict(SignalIdentifier)
        
    def visualize_by_prompt(
        self, prompt: str, task: str, file_path: str, output_png_path: str, conversation_history: List[Dict[str, str]] = None
    ):
        """
        Generate visualization based on prompt and data
        
        Args:
            prompt: The user's prompt
            task: The current task
            file_path: Path to the data file
            output_png_path: Path to save the output PNG
            conversation_history: List of previous conversation messages
        """
        
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            sample_data = df.head(5)
            
            print(f"The sample data: {sample_data}")
            print(f"The column names: {sample_data.columns}")
            print(f"Conversation history length: {len(conversation_history) if conversation_history else 0}")
            
            # Add conversation context to the prompt if available
            if conversation_history:
                context = "\n\nPrevious conversation context:\n"
                for msg in conversation_history[-3:]:  # Only use last 3 messages for context
                    role = "User" if msg["role"] == "user" else "Assistant"
                    context += f"{role}: {msg['content']}\n"
                prompt = prompt + context
            
            response = self.visualize(
                prompt=prompt,
                task=task,
                file_path=file_path,
                sample_data=sample_data,
            )
            plot_code = response.plot_code
            print(f"[DEBUG] Generated plot code:\n{plot_code}")
            
            # Clean up the code - remove markdown code blocks if present
            plot_code = re.sub(r"```python\s*", "", plot_code)
            plot_code = re.sub(r"```\s*", "", plot_code)
            
            try:
                # Create a new namespace with all required imports
                import plotly.graph_objects as go
                import json
                
                namespace = {
                    'pd': pd,
                    'json': json,
                    'go': go,
                    'file_path': file_path  # Also provide the file path
                }
                
                # Execute the code in the namespace with retry logic
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        # Execute the code in the namespace
                        exec(plot_code, namespace)
                        
                        # Get the figure from the namespace
                        if 'fig' not in namespace:
                            raise ValueError("Plot code did not create a 'fig' variable")
                        
                        fig = namespace['fig']
                        print("[INFO] Successfully created plotly figure")
                        
                        # Convert to JSON
                        fig_json = fig.to_json()
                        print("[INFO] Successfully converted figure to JSON")
                        
                        # Save the figure to the output png path
                        fig.write_image(output_png_path)
                        print(f"[INFO] Successfully saved figure to {output_png_path}")
                        
                        return fig_json
                        
                    except Exception as e:
                        last_error = e
                        retry_count += 1
                        print(f"[ERROR] Attempt {retry_count}/{max_retries} failed: {str(e)}")
                        import traceback
                        error_traceback = traceback.format_exc()
                        print(f"[ERROR] Traceback:\n{error_traceback}")
                        print(f"[ERROR] Plot code that failed:\n{plot_code}")
                        
                        if retry_count < max_retries:
                            # Prepare error context for the AI
                            error_context = f"""
The plot code failed with the following error:
Error: {str(e)}
Traceback:
{error_traceback}

Please fix the code and try again. Here's the code that failed:
{plot_code}
"""
                            # Get fixed code from the AI
                            response = self.visualize(
                                prompt=error_context,
                                task="Fix the plotting code based on the error message",
                                file_path=file_path,
                                sample_data=sample_data,
                            )
                            plot_code = response.plot_code
                            print(f"[INFO] Retrying with fixed code:\n{plot_code}")
                            
                            # Clean up the code again
                            plot_code = re.sub(r"```python\s*", "", plot_code)
                            plot_code = re.sub(r"```\s*", "", plot_code)
                            
                        else:
                            print("[ERROR] Max retries reached. Raising last error.")
                            raise last_error
                        
            except Exception as e:
                print(f"[ERROR] Failed to create plot: {str(e)}")
                import traceback
                traceback.print_exc()
                print(f"[ERROR] Plot code that failed:\n{plot_code}")
                raise
                
        except Exception as e:
            print(f"[ERROR] Failed to read or process file: {str(e)}")
            raise
    
    def identify_signal(self, prompt: str, file_path: str):
        """
        Identify the signal in the data
        """
        df = pd.read_csv(file_path)
        sample_data = df.head(5)
        response = self.signal_identifier(
            prompt=prompt,
            sample_data=sample_data
        ).signal_list
        
        result = [{'signal_name': signal.signal_name, 'signal_description': signal.signal_description} for signal in response]
        return result

# Run a quick test
if __name__ == "__main__":
    json_filepath = "data/retriever_results/20250405_021246_get_balance_0x1f9090aaE28b8a3dCeaDf281B0F12828e676.json"
    visualizer = VisualizerAgent(
        prompt="Is Ethereum suitable to invest right now?",
        task="Retrieve the current price and historical price trends of Ethereum.",
        file_path=json_filepath,
        output_png_path="data/visualization_results/20250405_021246_get_balance_0x1f9090aaE28b8a3dCeaDf281B0F12828e676.png"
    )
