import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import uuid
from typing import Dict, Any, Optional
import dspy
from agents.config import ModelConfig, get_model_config

class CodeGenerator(dspy.Signature):
    """
    You are a Python expert in data processing and financial analysis.
    Given a user's request and sample data, generate Python code to process the data.
    The code should:
    1. Read the CSV file using pd.read_csv(input_file)
    2. Process the data according to the requirements
    3. Save the processed data to output_file using df.to_csv(output_file, index=False)
    4. If possible, the new data should be new columns or new rows concatenated to the original data.
    5. The code will be directly executed. The namespace will be provided (input_file, output_file).
    """
    prompt = dspy.InputField(prefix="User's request:")
    sample_data = dspy.InputField(prefix="Sample data from CSV:")
    code = dspy.OutputField(prefix="Python code to process the data:")

class DataProcessor:
    """
    A class to process and transform CSV data based on user requirements.
    """
    
    def __init__(self):
        # Create data directory if it doesn't exist
        self.data_dir = Path("data/processed_data")
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize LLM for code generation
        model_config = get_model_config(ModelConfig.GPT4O)
        model = f"openai/{model_config['model_name']}"
        lm = dspy.LM(model=model, api_key=model_config['api_key'], base_url=model_config['base_url'])
        dspy.configure(lm=lm)
        self.generate_code = dspy.Predict(CodeGenerator)

    def process_with_code(
        self,
        file_path: str,
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process CSV data using LLM-generated code
        
        Args:
            file_path: Path to the input CSV file
            prompt: User's request for data processing
        
        Returns:
            Dict containing:
                - file_path: Path to the processed CSV file
                - df_head: Preview of the processed data
                - code: The generated code used for processing
        """
        try:
            # Ensure input file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Input file not found: {file_path}")
            
            # Read sample data for code generation
            df = pd.read_csv(file_path)
            sample_data = df.head().to_string()
            
            # Generate code using LLM
            response = self.generate_code(
                prompt=prompt,
                sample_data=sample_data
            )
            code = response.code
            
            # Clean up the code - remove markdown code blocks if present
            code = code.replace("```python", "").replace("```", "").strip()
            
            # Generate output file path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_id = str(uuid.uuid4())
            output_file = self.data_dir / f"processed_data_{timestamp}_{file_id}.csv"
            
            # Create namespace for code execution
            namespace = {
                'pd': pd,
                'input_file': file_path,
                'output_file': str(output_file)
            }
            
            print(namespace)
            
            print("\nGenerated code:")
            print("="*50)
            print(code)
            print("="*50)
            
            # Execute the generated code
            print("\nExecuting code...")
            exec(code, namespace)
            
            # Print execution results
            print("\nExecution results:")
            print("="*50)
            if 'df' in namespace:
                print("\nDataFrame after processing:")
                print(namespace['df'].head())
            print("="*50)
            
            # Verify output file exists
            if not os.path.exists(output_file):
                raise FileNotFoundError(f"Output file was not created: {output_file}")
            
            # Read the processed data
            processed_df = pd.read_csv(output_file)
            
            return {
                "file_path": str(output_file),
                "df_head": processed_df.head().to_string(),
                "code": code
            }
            
        except Exception as e:
            print(f"Error processing data with code: {str(e)}")
            import traceback
            print("\nFull error traceback:")
            print(traceback.format_exc())
            return None

