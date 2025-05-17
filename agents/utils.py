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

    def get_ohlcv(self,
                  id: str = None,
                  slug: str = None,
                  symbol: str = None,
                  time_period: str = "daily",
                  time_start: str = None,
                  time_end: str = None,
                  count: int = 10,
                  interval: str = "daily",
                  convert: str = "USD",
                  convert_id: str = None,
                  skip_invalid: bool = True) -> pd.DataFrame:
        """
        Get historical OHLCV data for cryptocurrencies
        
        Args:
            id (str, optional): One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,1027"
            slug (str, optional): Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum"
            symbol (str, optional): Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH"
            time_period (str, optional): Time period to return OHLCV data for. Options: "daily", "hourly". Defaults to "daily"
            time_start (str, optional): Start time in ISO format (e.g., '2023-01-01')
            time_end (str, optional): End time in ISO format (e.g., '2023-12-31')
            count (int, optional): Limit the number of time periods to return. Defaults to 10, max 10000
            interval (str, optional): Adjust the interval that time_period is sampled. Options:
                - Hours: "1h", "2h", "3h", "4h", "6h", "12h"
                - Days: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d"
                - Other: "hourly", "daily", "weekly", "monthly", "yearly"
            convert (str, optional): Currency to convert to. Defaults to "USD"
            convert_id (str, optional): Calculate market quotes by CoinMarketCap ID instead of symbol
            skip_invalid (bool, optional): Skip invalid cryptocurrencies. Defaults to True
            
        Returns:
            pd.DataFrame: DataFrame containing OHLCV data with symbol and OHLCV columns
        """
        endpoint = f"{self.base_url}/cryptocurrency/ohlcv/historical"
        
        # Validate required parameters
        if not any([id, slug, symbol]):
            raise ValueError("At least one of id, slug, or symbol must be provided")
            
        params = {
            "time_period": time_period,
            "interval": interval,
            "count": count,
            "skip_invalid": str(skip_invalid).lower()
        }
        
        # Add optional parameters if provided
        if id:
            params["id"] = id
        if slug:
            params["slug"] = slug
        if symbol:
            params["symbol"] = symbol
        if time_start:
            params["time_start"] = time_start
        if time_end:
            params["time_end"] = time_end
        if convert:
            params["convert"] = convert
        if convert_id:
            params["convert_id"] = convert_id
            
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
                
            # Process the response data
            all_data = []
            crypto_data = data['data']
            
            if not isinstance(crypto_data, dict):
                print("Invalid data format")
                return pd.DataFrame()
                
            quotes = crypto_data.get('quotes')
            if not quotes:
                print("No quotes data found")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame(quotes)
            
            # Convert timestamp to datetime
            df['time_open'] = pd.to_datetime(df['time_open'])
            df.set_index('time_open', inplace=True)
            
            # Extract quote data
            quote_currency = list(df['quote'].iloc[0].keys())[0]  # Get the first quote currency
            df = pd.json_normalize(df['quote'].apply(lambda x: x[quote_currency]))
            
            # Add symbol
            df['symbol'] = crypto_data.get('symbol', '')
            
            # Reorder columns to only include symbol and OHLCV
            final_df = df[['symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            print("\nFinal DataFrame structure:")
            print(final_df.head())
            
            return final_df
            
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