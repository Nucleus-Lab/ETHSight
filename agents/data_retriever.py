import dspy
from agents.config import ModelConfig, get_model_config
from agents.utils import BitqueryAPI
import os
from datetime import datetime, timezone
import pandas as pd
import json
import uuid
from pathlib import Path
from agents.prompt import GRAPHQL_RULES


class GraphQLQuery(dspy.Signature):
    """You are an expert in Bitquery GraphQL. The user is asking for specific data about Uniswap tokens, and you need to write a GraphQL query to retrieve the data from the Bitquery.
    
    # Example Output
    {
    EVM(dataset: combined, network: eth) {
        DEXTradeByTokens(
        orderBy: {descendingByField: "volumeUsd"}
        limit: {count: 10}
        where: {Trade: {Dex: {ProtocolName: {is: "uniswap_v3"}}}}
        ) {
        Trade {
            Currency {
            SmartContract
            Symbol
            Name
            }
            Dex {
            ProtocolName
            }
        }
        volumeUsd: sum(of: Trade_Side_AmountInUSD)
        count
        }
      }
    }
    
    # Guidelines
    1. You only have to access the `DEXTradeByTokens` table
    2. You should limit the query to `where: {Trade: {Dex: {ProtocolName: {is: "uniswap_v3"}}}}`
    3. You should directly return the GraphQL query, without any other text.
    4. For datetime fields, use the format: "YYYY-MM-DDTHH:mm:ssZ" (e.g., "2024-03-21T14:30:22Z")
    5. You must be aware of the GraphQL syntax. Do not miss out any parenthesis.
    """
    query = dspy.InputField(prefix="User's prompt:")
    table_context = dspy.InputField(prefix="Table context:")
    current_time = dspy.InputField(prefix="Current date and time:")
    graphql_query = dspy.OutputField(prefix="The GraphQL query:")

class BitqueryDataRetriever():
    def __init__(self):
        model_config = get_model_config(ModelConfig.GPT4O)
        model = f"openai/{model_config['model_name']}"
        lm = dspy.LM(model=model, api_key=model_config['api_key'], base_url=model_config['base_url'])
        dspy.configure(lm=lm)
        self.generate_query = dspy.Predict(GraphQLQuery)
        self.BitqueryAPI = BitqueryAPI(os.getenv("BITQUERY_API_KEY"))
        
        # Create data directory if it doesn't exist
        self.data_dir = Path("data/bitquery_data")
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str = '.') -> dict:
        """
        Flatten a nested dictionary
        
        Args:
            d (dict): Nested dictionary to flatten
            parent_key (str): Parent key for nested items
            sep (str): Separator for nested keys
            
        Returns:
            dict: Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _extract_data(self, data: dict) -> list:
        """
        Extract data from nested structure recursively
        
        Args:
            data (dict): Nested data structure
            
        Returns:
            list: List of flattened dictionaries
        """
        if not isinstance(data, dict):
            return []
            
        # If the data contains a list, process each item
        for key, value in data.items():
            if isinstance(value, list):
                return [self._flatten_dict(item) for item in value]
            elif isinstance(value, dict):
                return self._extract_data(value)
        
        return [self._flatten_dict(data)]
    
    def convert_to_csv(self, data: dict, output_file: str):
        """
        Convert nested Bitquery data to CSV format
        
        Args:
            data (dict): Raw data from Bitquery API
            output_file (str): Path to save the CSV file
            
        Returns:
            pd.DataFrame: DataFrame containing the flattened data
        """
        try:
            # Extract and flatten the data
            flattened_data = self._extract_data(data)
            
            if not flattened_data:
                print("No data to convert")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(flattened_data)
            
            # Save to CSV
            df.to_csv(output_file, index=False)
            print(f"Data saved to {output_file}")
            
            return df
            
        except Exception as e:
            print(f"Error converting data to CSV: {e}")
            return None
    
    
    def get_data(self, query: str = None, graphql_query: str = None):
        # Get current time in UTC with proper format
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if graphql_query is None:
            graphql_query = self.generate_query(
                query=query,
                current_time=current_time,
                table_context=GRAPHQL_RULES
            ).graphql_query
        
        print(graphql_query)
        data = self.BitqueryAPI.request(query=graphql_query)
        if data:
            # Generate unique filename with UUID
            file_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = str(self.data_dir / f"bitquery_data_{timestamp}_{file_id}.csv")
            
            df = self.convert_to_csv(data, file_path)
            if df is not None:
                return {
                    "file_path": file_path,
                    "df_head": df.head().to_string(),
                    "description": "Data retrieved from Bitquery"
                }
        return None
    



