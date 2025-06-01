#!/usr/bin/env python
"""
Strategy Interface Module
Simplified interface for strategy.py to interact with backtesting system
"""

import os
import sys
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
import pandas as pd

# Add the parent directory to the path to import backtest_utils modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_utils.geckoterminal_backtracker.storage.csv_storage import CSVStorage
from backtest_utils.geckoterminal_backtracker.storage.sqlite_storage import SQLiteStorage
from backtest_utils.geckoterminal_backtracker.api.gecko_api import GeckoTerminalAPI
from backtest_utils.geckoterminal_backtracker.utils.data_fetcher import OHLCDataFetcher
from backtest_utils.geckoterminal_backtracker.analysis.ai_indicator_runner import generate_ai_indicator as _generate_ai_indicator
from backtest_utils.geckoterminal_backtracker.analysis.indicator_backtester import (
    find_indicator_file, backtest_indicators, plot_backtest_results, resample_ohlc
)


def generate_indicator_from_prompt(user_prompt: str, indicator_name: str, api_key: str = None, model: str = 'gpt-4o'):
    """
    Generate AI indicator from user prompt
    
    Args:
        user_prompt (str): Natural language description of the indicator
        indicator_name (str): Name for the indicator
        api_key (str, optional): OpenAI API key. If None, uses environment variable
        model (str): OpenAI model to use
        
    Returns:
        tuple: (indicator_file_path, indicator_name)
    """
    print(f"Generating AI indicator: {indicator_name}")
    print(f"Description: {user_prompt}")
    
    # Create indicators directory if it doesn't exist
    indicators_dir = 'indicators'
    os.makedirs(indicators_dir, exist_ok=True)
    
    # Create arguments for the AI indicator generator
    args = SimpleNamespace(
        description=user_prompt,
        name=indicator_name,
        save=True,
        output_dir=indicators_dir,
        model=model,
        api_key=api_key
    )
    
    try:
        # Generate the indicator
        _generate_ai_indicator(args)
        
        # Construct the expected file path
        file_name = f"{indicator_name.lower().replace(' ', '_')}.py"
        file_path = os.path.join(indicators_dir, file_name)
        
        # Verify the file was created
        if os.path.exists(file_path):
            print(f"Successfully generated indicator: {file_path}")
            return file_path, indicator_name
        else:
            raise Exception(f"Indicator file was not created at {file_path}")
            
    except Exception as e:
        print(f"Error generating indicator: {str(e)}")
        raise


def search_and_get_pool_address(network: str, token_symbol: str):
    """
    Search for pool address using token symbol
    
    Args:
        network (str): Network ID (e.g., 'eth', 'bsc')
        token_symbol (str): Token symbol to search for
        
    Returns:
        str: Pool address
    """
    print(f"Searching for {token_symbol} pools on {network} network...")
    
    # Create API client
    api = GeckoTerminalAPI()
    
    # Search for pools with the corrected method signature
    pools = api.search_pools(
        network=network,
        query=token_symbol,
        page=1,
        include=['base_token', 'quote_token', 'dex']
    )
    
    if not pools:
        print(f"No pools found for {token_symbol} on {network}, trying without network filter...")
        # Try searching across all networks if no results found
        pools = api.search_pools(
            query=token_symbol,
            page=1,
            include=['base_token', 'quote_token', 'dex']
        )
        
        if not pools:
            raise Exception(f"No pools found for {token_symbol}")
    
    # Get the first pool (most relevant)
    pool = pools[0]
    pool_address = pool.get('attributes', {}).get('address')
    
    if not pool_address:
        raise Exception(f"Could not get pool address for {token_symbol}")
    
    print(f"Found pool address: {pool_address}")
    
    # Print some additional pool information for debugging
    attributes = pool.get('attributes', {})
    pool_name = attributes.get('name', 'Unknown')
    base_token = attributes.get('base_token_price_usd', 'Unknown')
    print(f"Pool name: {pool_name}")
    print(f"Base token price: ${base_token}")
    
    return pool_address


def fetch_ohlc_data(network: str, pool_address: str, timeframe: str, time_start: str, time_end: str):
    """
    Fetch OHLC data from GeckoTerminal
    
    Args:
        network (str): Network ID
        pool_address (str): Pool address
        timeframe (str): Timeframe (e.g., '1m', '15m', '1h', '1d')
        time_start (str): Start time in ISO format
        time_end (str): End time in ISO format
        
    Returns:
        str: Path to saved CSV file
    """
    print(f"Fetching OHLC data for {network}/{pool_address}")
    
    # Convert timeframe to GeckoTerminal format
    timeframe_map = {
        '1m': ('minute', 1),
        '5m': ('minute', 5),
        '15m': ('minute', 15),
        '1h': ('hour', 1),
        '4h': ('hour', 4),
        '1d': ('day', 1),
        'day': ('day', 1),
        'hour': ('hour', 1),
        'minute': ('minute', 1)
    }
    
    if timeframe not in timeframe_map:
        # Default mapping
        if 'm' in timeframe:
            tf, agg = 'minute', int(timeframe.replace('m', ''))
        elif 'h' in timeframe:
            tf, agg = 'hour', int(timeframe.replace('h', ''))
        elif 'd' in timeframe:
            tf, agg = 'day', int(timeframe.replace('d', ''))
        else:
            tf, agg = 'day', 1
    else:
        tf, agg = timeframe_map[timeframe]
    
    # Calculate days back from time range
    start_date = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
    days_back = (end_date - start_date).days + 1
    
    # Create data directory
    data_dir = 'data'
    os.makedirs(data_dir, exist_ok=True)
    
    # Create storage handler
    storage = CSVStorage(data_dir)
    
    # Create data fetcher
    fetcher = OHLCDataFetcher()
    
    # Fetch and store data
    df = fetcher.fetch_and_store(
        network=network,
        pool_address=pool_address,
        timeframe=tf,
        aggregate=agg,
        days_back=days_back,
        storage_handlers=[storage]
    )
    
    if df.empty:
        raise Exception("No data fetched from GeckoTerminal")
    
    # Generate file path for the data
    import uuid
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(data_dir, f"gecko_{network}_{pool_address}_{tf}_{agg}_{timestamp}_{file_id}.csv")
    
    # Save data to CSV
    df.to_csv(file_path, index=False)
    
    print(f"Data saved to: {file_path}")
    print(f"Data points: {len(df)}")
    
    return file_path


def run_backtest_with_indicators(
    network: str, 
    token_symbol: str, 
    timeframe: str, 
    time_start: str, 
    time_end: str,
    buy_indicator_name: str,
    sell_indicator_name: str = None
):
    """
    Run backtest with given indicators
    
    Args:
        network (str): Network ID (e.g., 'eth', 'bsc')
        token_symbol (str): Token symbol
        timeframe (str): Timeframe (e.g., '1m', '15m', '1h', '1d')
        time_start (str): Start time in ISO format
        time_end (str): End time in ISO format
        buy_indicator_name (str): Name of buy indicator
        sell_indicator_name (str, optional): Name of sell indicator
        
    Returns:
        dict: Dictionary containing trading stats and plotly figure JSON
    """
    try:
        print(f"Running backtest for {token_symbol} on {network}")
        
        # Step 1: Search for pool address
        pool_address = search_and_get_pool_address(network, token_symbol)
        
        # Step 2: Fetch OHLC data
        data_file_path = fetch_ohlc_data(network, pool_address, timeframe, time_start, time_end)
        
        # Step 3: Load data from CSV
        df = pd.read_csv(data_file_path)
        
        # Ensure datetime column exists and is properly formatted
        if 'datetime' not in df.columns:
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'])
            else:
                # Create datetime from index if needed
                df['datetime'] = pd.to_datetime(df.index)
        else:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Sort by datetime
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Step 4: Find indicator files
        indicators_dir = 'indicators'
        
        buy_indicator_file = find_indicator_file(buy_indicator_name, indicators_dir)
        if not buy_indicator_file:
            raise Exception(f"Buy indicator '{buy_indicator_name}' not found")
        
        sell_indicator_file = None
        if sell_indicator_name:
            sell_indicator_file = find_indicator_file(sell_indicator_name, indicators_dir)
            if not sell_indicator_file:
                raise Exception(f"Sell indicator '{sell_indicator_name}' not found")
        
        # Step 5: Run backtest
        result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns = backtest_indicators(
            df, 
            buy_indicator_name, 
            sell_indicator_name, 
            None,  # buy_column (auto-detect)
            None,  # sell_column (auto-detect)
            indicators_dir
        )
        
        # Step 6: Generate plot
        json_dir = 'json_charts'
        os.makedirs(json_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if sell_indicator_info:
            json_name = f"{network}_{token_symbol}_{buy_indicator_info['name']}_and_{sell_indicator_info['name']}_{timestamp}.json"
            title = f"{buy_indicator_info['name']} (Buy) + {sell_indicator_info['name']} (Sell) - {network.upper()}:{token_symbol}"
        else:
            json_name = f"{network}_{token_symbol}_{buy_indicator_info['name']}_{timestamp}.json"
            title = f"{buy_indicator_info['name']} - {network.upper()} {token_symbol}"
        
        json_path = os.path.join(json_dir, json_name)
        
        # Generate plot
        fig = plot_backtest_results(
            result_df, 
            buy_indicator_info, 
            sell_indicator_info, 
            buy_signal_columns, 
            sell_signal_columns,
            title=title,
            save_path=None,
            save_json=json_path,
            network=network,
            pool=pool_address,
            timeframe=timeframe,
            aggregate=1
        )
        
        # Prepare result
        result = {
            'trading_stats': stats,
            'plotly_figure': fig.to_json() if fig else None,
            'buy_indicator_info': buy_indicator_info,
            'sell_indicator_info': sell_indicator_info,
            'data_points': len(result_df),
            'time_range': {
                'start': df['datetime'].min().isoformat(),
                'end': df['datetime'].max().isoformat()
            }
        }
        
        print("Backtest completed successfully")
        print(f"Trading stats: {stats}")
        
        return result
        
    except Exception as e:
        print(f"Error running backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        raise 