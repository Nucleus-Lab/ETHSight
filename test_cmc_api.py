from dotenv import load_dotenv
load_dotenv()

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from agents.utils import CMCAPI

def main():
    # Initialize CMC API client
    api_key = os.getenv("CMC_API_KEY")
    if not api_key:
        print("Error: CMC_API_KEY not found in environment variables")
        return
        
    cmc = CMCAPI(api_key=api_key)
    
    # Test case: Get WETH daily data for the last 7 days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    print(f"API Key: {api_key[:5]}...{api_key[-5:]}")  # Show first and last 5 chars of API key
    print(f"Time range: {start_time} to {end_time}")
    
    print("\nFetching WETH daily OHLCV data for the last 7 days...")
    try:
        weth_data = cmc.get_historical_quotes(
            symbol="WETH",
            time_start=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            time_end=end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            interval="1d"
        )
        
        if weth_data.empty:
            print("\nNo data returned. Possible reasons:")
            print("1. API key doesn't have access to historical data")
            print("2. Symbol 'WETH' might not be supported")
            print("3. No data available for the specified time range")
        else:
            print("\nData Preview:")
            print(weth_data)
            
            print("\nData Info:")
            print(weth_data.info())
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check if your API key is valid")
        print("2. Verify your API plan includes historical data access")
        print("3. Try with a different symbol (e.g., 'BTC' or 'ETH')")
        print("4. Check CMC API documentation for supported symbols")

if __name__ == "__main__":
    main()