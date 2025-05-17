import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import uuid

class BitqueryAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://streaming.bitquery.io/graphql"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def request(self, query: str, variables: dict = None):
        """
        Make a request to Bitquery API
        
        Args:
            query (str): GraphQL query string
            variables (dict, optional): Variables for the query. Defaults to None.
            
        Returns:
            dict: Response data or None if error
        """
        try:
            payload = {
                "query": query,
                "variables": variables or {}
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None

class CMCAPI:
    def __init__(self, api_key):
        """
        Initialize CMC API client
        
        Args:
            api_key (str): CoinMarketCap API key
        """
        self.api_key = api_key
        self.base_url = "https://pro-api.coinmarketcap.com/v2"
        self.headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json"
        }

    def get_historical_quotes(self,
                            symbol: str,
                            time_start: str = None,
                            time_end: str = None,
                            interval: str = "1d",
                            convert: str = "USD") -> pd.DataFrame:
        """
        Get historical OHLCV data for a cryptocurrency
        
        Args:
            symbol (str): Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            time_start (str, optional): Start time in ISO format (e.g., '2023-01-01')
            time_end (str, optional): End time in ISO format (e.g., '2023-12-31')
            interval (str, optional): Time interval. Options:
                - Hours: '1h', '2h', '3h', '4h', '6h', '12h'
                - Days: '1d', '2d', '3d', '7d', '14d', '15d', '30d', '60d', '90d', '365d'
            convert (str, optional): Currency to convert to. Defaults to 'USD'
            
        Returns:
            pd.DataFrame: DataFrame containing OHLCV data
        """
        endpoint = f"{self.base_url}/cryptocurrency/ohlcv/historical"
        
        # Determine time_period based on interval
        time_period = "hourly" if interval.endswith("h") else "daily"
        
        params = {
            "symbol": symbol,
            "time_period": time_period,
            "interval": interval,
            "convert": convert
        }
        
        if time_start:
            params["time_start"] = time_start
        if time_end:
            params["time_end"] = time_end
            
        try:
            print(f"\nMaking request to CMC API:")
            print(f"Endpoint: {endpoint}")
            print(f"Params: {params}")
            
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params
            )
            
            print(f"\nResponse status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return pd.DataFrame()
                
            data = response.json()
            print(f"\nResponse data: {json.dumps(data, indent=2)}")
            
            if not data.get('data'):
                print("No data found in response")
                return pd.DataFrame()
                
            # Get the first item from the symbol array
            symbol_data = data['data'].get(symbol)
            if not symbol_data or not isinstance(symbol_data, list) or len(symbol_data) == 0:
                print(f"No data found for symbol {symbol}")
                return pd.DataFrame()
                
            quotes = symbol_data[0].get('quotes')
            if not quotes:
                print("No quotes data found")
                return pd.DataFrame()
            
            # Print the structure of the first quote to understand the data format
            if quotes and len(quotes) > 0:
                print("\nFirst quote structure:")
                print(json.dumps(quotes[0], indent=2))
            
            # Convert to DataFrame
            df = pd.DataFrame(quotes)
            
            # Convert timestamp to datetime
            df['time_open'] = pd.to_datetime(df['time_open'])
            df.set_index('time_open', inplace=True)
            
            # Extract USD quote data
            df = pd.json_normalize(df['quote'].apply(lambda x: x['USD']))
            
            # Rename columns to match standard OHLCV format
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Reorder columns to match standard OHLCV format
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Print the final DataFrame structure
            print("\nFinal DataFrame structure:")
            import pdb; pdb.set_trace()
            print(df.head())
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from CMC: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response text: {e.response.text}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return pd.DataFrame()
            
    def _save_to_csv(self, df: pd.DataFrame, symbol: str, interval: str) -> dict:
        """
        Save DataFrame to CSV file
        
        Args:
            df (pd.DataFrame): DataFrame to save
            symbol (str): Cryptocurrency symbol
            interval (str): Time interval
            
        Returns:
            dict: Dictionary containing file path and data preview
        """
        try:
            # Create data directory if it doesn't exist
            data_dir = Path("data/cmc_data")
            data_dir.mkdir(exist_ok=True, parents=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_id = str(uuid.uuid4())
            file_path = str(data_dir / f"cmc_{symbol}_{interval}_{timestamp}_{file_id}.csv")
            
            # Save to CSV
            df.to_csv(file_path)
            print(f"Data saved to {file_path}")
            
            return {
                "file_path": file_path,
                "df_head": df.head().to_string(),
                "description": f"CMC historical OHLCV data for {symbol} with {interval} interval"
            }
            
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
            return None 