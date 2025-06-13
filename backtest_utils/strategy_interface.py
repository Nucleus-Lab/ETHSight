#!/usr/bin/env python
"""
Strategy Interface Module
Simplified interface for strategy.py to interact with backtesting system
"""

import os
import sys
import traceback
from decimal import Decimal
from datetime import datetime, timedelta
from types import SimpleNamespace
import pandas as pd
import numpy as np

# Add the parent directory to the path to import backtest_utils modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_utils.geckoterminal_backtracker.storage.csv_storage import CSVStorage
from backtest_utils.geckoterminal_backtracker.storage.sqlite_storage import SQLiteStorage
from backtest_utils.geckoterminal_backtracker.api.gecko_api import GeckoTerminalAPI
from backtest_utils.geckoterminal_backtracker.utils.data_fetcher import OHLCDataFetcher
from backtest_utils.geckoterminal_backtracker.analysis.ai_indicator_runner import generate_ai_indicator as _generate_ai_indicator
from backtest_utils.geckoterminal_backtracker.analysis.indicator_backtester import (
    find_indicator_file, backtest_indicators, plot_backtest_results, resample_ohlc, calculate_trading_stats
)


def generate_indicator_code_from_prompt(prompt: str, model: str = 'gpt-4o', api_key: str = None) -> str:
    """
    Generate indicator code from natural language prompt
    
    Args:
        prompt (str): Natural language description of the indicator
        model (str): OpenAI model to use (default: 'gpt-4o')
        api_key (str, optional): OpenAI API key. If None, uses environment variable
        
    Returns:
        str: Generated Python indicator code
    """
    print(f"Generating indicator code from prompt...")
    print(f"Prompt: {prompt}")
    print(f"Model: {model}")
    
    try:
        # Import AIIndicatorGenerator here to avoid circular imports
        from backtest_utils.geckoterminal_backtracker.analysis.ai_indicator_generator import AIIndicatorGenerator
        
        # Initialize the generator
        generator = AIIndicatorGenerator(api_key=api_key)
        
        # Generate the indicator code
        code = generator.generate_indicator_code(prompt, model)
        
        print("Successfully generated indicator code")
        return code
        
    except Exception as e:
        print(f"Error generating indicator code: {str(e)}")
        print(traceback.format_exc())
        raise Exception(f"Failed to generate indicator code: {str(e)}")


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
        print(traceback.format_exc())
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
    buy_indicator_code: str,
    sell_indicator_code: str = None,
    buy_indicator_name: str = None,
    sell_indicator_name: str = None
):
    """
    Run backtest with provided indicator codes
    
    Args:
        network (str): Network to fetch data from (e.g., 'eth', 'bsc')
        token_symbol (str): Token symbol (e.g., 'ETH', 'BTC')
        timeframe (str): Timeframe for OHLC data (e.g., '1m', '15m', '1h', '1d')
        time_start (str): Start time in ISO format
        time_end (str): End time in ISO format
        buy_indicator_code (str): Python code for buy indicator
        sell_indicator_code (str, optional): Python code for sell indicator
        buy_indicator_name (str, optional): Name for buy indicator
        sell_indicator_name (str, optional): Name for sell indicator
        
    Returns:
        dict: Dictionary containing backtest results
    """
    print(f"Running backtest for {network}:{token_symbol} ({timeframe})")
    print(f"Time range: {time_start} to {time_end}")
    
    # Set default names if not provided
    if not buy_indicator_name:
        buy_indicator_name = "buy_indicator"
    if not sell_indicator_name and sell_indicator_code:
        sell_indicator_name = "sell_indicator"
    
    try:
        # Step 1: Search for pool address
        pool_address = search_and_get_pool_address(network, token_symbol)
        print(f"Found pool address: {pool_address}")
        
        # Step 2: Fetch OHLC data
        # fetch_ohlc_data returns a file path, not a DataFrame
        data_file_path = fetch_ohlc_data(network, pool_address, timeframe, time_start, time_end)
        
        # Read the CSV file to get the DataFrame
        print(f"Reading data from: {data_file_path}")
        df = pd.read_csv(data_file_path)
        
        print(f"DataFrame columns before sorting: {list(df.columns)}")
        
        # Ensure datetime column exists and is properly formatted
        if 'datetime' not in df.columns:
            print("datetime not in df.columns")
            if 'timestamp' in df.columns:
                print(f"Timestamp column in df")
                df['datetime'] = pd.to_datetime(df['timestamp'])
            else:
                print("timestamp not in df.columns")
                # Create datetime from index if needed
                df['datetime'] = pd.to_datetime(df.index)
        else:
            print("datetime in df.columns")
            df['datetime'] = pd.to_datetime(df['datetime'])
            
        # Sort by datetime and set as index
        df = df.sort_values('datetime')
        print(f"DataFrame columns after sorting: {list(df.columns)}")
        
        if df.empty:
            raise Exception("No data available for the specified time range")
            
        print(f"Loaded {len(df)} data points")
        
        # Step 3: Apply indicators using provided codes
        print(f"Applying buy indicator: {buy_indicator_name}")
        df = apply_indicator_code(df, buy_indicator_code, buy_indicator_name)
        print(f"DataFrame columns after buy indicator: {list(df.columns)}")
        
        sell_indicator_info = None
        if sell_indicator_code:
            print(f"Applying sell indicator: {sell_indicator_name}")
            df = apply_indicator_code(df, sell_indicator_code, sell_indicator_name)
            print(f"DataFrame columns after sell indicator: {list(df.columns)}")
            sell_indicator_info = {"name": sell_indicator_name}
        
        buy_indicator_info = {"name": buy_indicator_name}
        
        # Check for signal columns
        signal_columns = [col for col in df.columns if 'signal' in col.lower()]
        print(f"Available signal columns: {signal_columns}")
        
        # Show sample of signal data
        for col in signal_columns:
            if col in df.columns:
                signal_count = df[col].sum() if df[col].dtype in ['int64', 'int32', 'bool'] else 'N/A'
                print(f"Signal column '{col}' has {signal_count} signals")
        
        # Step 5: Run backtest
        result_df, buy_indicator_info, sell_indicator_info, stats, buy_signal_columns, sell_signal_columns = backtest_indicators(
            df, 
            buy_indicator_name, 
            sell_indicator_name, 
            None,  # buy_column (auto-detect)
            None,  # sell_column (auto-detect)
            'indicators',  # indicators_dir (not used when use_existing_indicators=True)
            use_existing_indicators=True  # Use indicators already applied to DataFrame
        )
        
        # Step 5: Generate plot
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
        
        # Convert figure to JSON
        plotly_json = fig.to_json()
        
        print(f"Backtest completed successfully")
        print(f"Trading stats: {stats}")
        
        return {
            'trading_stats': stats,
            'plotly_figure': plotly_json,
            'buy_indicator_info': buy_indicator_info,
            'sell_indicator_info': sell_indicator_info,
            'data_points': len(df),
            'time_range': {
                'start': df.iloc[0]['datetime'].isoformat() if not df.empty else time_start,
                'end': df.iloc[-1]['datetime'].isoformat() if not df.empty else time_end
            }
        }
        
    except Exception as e:
        print(f"Error in backtest: {str(e)}")
        print(traceback.format_exc())
        raise

def apply_indicator_code(df: pd.DataFrame, indicator_code: str, indicator_name: str) -> pd.DataFrame:
    """Apply indicator code to DataFrame"""
    try:
        # Create a local namespace for execution
        local_vars = {'df': df.copy(), 'pd': pd, 'np': np}
        
        print("indicator_code in apply_indicator_code: ", indicator_code)
        
        # Execute the indicator code
        exec(indicator_code, globals(), local_vars)
        
        # Return the modified DataFrame
        return local_vars['df']
        
    except Exception as e:
        print(f"Error applying indicator {indicator_name}: {e}")
        print(traceback.format_exc())
        raise Exception(f"Failed to apply indicator {indicator_name}: {str(e)}")

# Removed unused backtest_indicators_with_df function - now using backtest_indicators with use_existing_indicators=True 

def generate_signal_calculation_code_from_prompt(signal_description: str, signal_name: str, model: str = 'gpt-4o', api_key: str = None) -> str:
    """
    Generate signal calculation code from natural language prompt (only calculates signal values, not buy/sell signals)
    
    Args:
        signal_description (str): Natural language description of the signal
        signal_name (str): Name for the signal column
        model (str): OpenAI model to use (default: 'gpt-4o')
        api_key (str, optional): OpenAI API key. If None, uses environment variable
        
    Returns:
        str: Generated Python code for signal calculation
    """
    print(f"Generating signal calculation code...")
    print(f"Signal: {signal_name}")
    print(f"Description: {signal_description}")
    print(f"Model: {model}")
    
    try:
        # Import AIIndicatorGenerator here to avoid circular imports
        from backtest_utils.geckoterminal_backtracker.analysis.ai_indicator_generator import AIIndicatorGenerator
        
        # Initialize the generator
        generator = AIIndicatorGenerator(api_key=api_key)
        
        # Generate the signal calculation code
        code = generator.generate_signal_calculation_code(signal_description, signal_name, model)
        
        print("Successfully generated signal calculation code")
        return code
        
    except Exception as e:
        print(f"Error generating signal calculation code: {str(e)}")
        print(traceback.format_exc())
        raise Exception(f"Failed to generate signal calculation code: {str(e)}")


def apply_signal_calculation_code(df: pd.DataFrame, signal_code: str, signal_name: str) -> tuple:
    """
    Apply signal calculation code to DataFrame
    
    Args:
        df (pd.DataFrame): Input DataFrame
        signal_code (str): Python code for signal calculation
        signal_name (str): Expected signal name
        
    Returns:
        tuple: (df_with_signal, signal_column_name)
    """
    try:
        # Create a local namespace for execution
        local_vars = {'df': df.copy(), 'pd': pd, 'np': np}
        
        print(f"Applying signal calculation code for: {signal_name}")
        print(f"Input DataFrame columns: {list(df.columns)}")
        print(f"DataFrame shape: {df.shape}")

        # Execute the signal calculation code
        exec(signal_code, globals(), local_vars)
        
        print(f"After execution, local_vars keys: {list(local_vars.keys())}")
        
        # Check if the function was executed and returned results
        updated_df = local_vars.get('df')
        signal_column = local_vars.get('signal_column', signal_name)
        
        # If the function was defined but not executed, execute it manually
        if 'calculate_signal' in local_vars and (signal_column == signal_name and signal_column not in updated_df.columns):
            print("Function defined but not executed, running manually...")
            calculate_signal_func = local_vars['calculate_signal']
            updated_df, signal_column = calculate_signal_func(updated_df)
            print(f"Manual execution completed, signal column: {signal_column}")
        
        if updated_df is not None:
            print(f"Updated DataFrame columns: {list(updated_df.columns)}")
            
            # Verify the signal column exists
            if signal_column in updated_df.columns:
                print(f"✅ Signal column '{signal_column}' successfully identified/added")
                
                # Check if this was an existing column or newly calculated
                if signal_column in df.columns:
                    print(f"   📋 Used existing column: {signal_column}")
                else:
                    print(f"   🧮 Calculated new column: {signal_column}")
                
                # Show signal statistics
                if updated_df[signal_column].dtype in ['int64', 'int32', 'float64', 'float32']:
                    signal_stats = updated_df[signal_column].describe()
                    print(f"   📊 Signal stats: min={signal_stats['min']:.2f}, max={signal_stats['max']:.2f}, mean={signal_stats['mean']:.2f}")
                else:
                    print(f"   📊 Signal data type: {updated_df[signal_column].dtype}")
                
                return updated_df, signal_column
            else:
                # Try to find any new columns that were added
                new_columns = [col for col in updated_df.columns if col not in df.columns]
                if new_columns:
                    print(f"Found new columns: {new_columns}")
                    return updated_df, new_columns[0]  # Use the first new column
                else:
                    raise ValueError(f"Signal column '{signal_column}' was not found in DataFrame")
        else:
            raise ValueError("DataFrame was not updated after code execution")
        
    except Exception as e:
        print(f"❌ Error applying signal calculation code for {signal_name}: {e}")
        print(f"Code that failed:\n{signal_code}")
        print(traceback.format_exc())
        raise Exception(f"Failed to apply signal calculation code for {signal_name}: {str(e)}")


def apply_condition_to_signal(df: pd.DataFrame, signal_column: str, operator: str, threshold: float, condition_type: str = 'buy') -> pd.DataFrame:
    """
    Apply condition (operator + threshold) to signal column to generate buy/sell signals
    
    Args:
        df (pd.DataFrame): DataFrame with signal column
        signal_column (str): Name of the signal column
        operator (str): Comparison operator ('>', '<', '>=', '<=', '==', '!=')
        threshold (float): Threshold value
        condition_type (str): 'buy' or 'sell' to determine which signal column to create
        
    Returns:
        pd.DataFrame: DataFrame with buy_signal or sell_signal column added
    """
    try:
        print(f"Applying {condition_type} condition: {signal_column} {operator} {threshold}")
        print(f"Input DataFrame columns: {list(df.columns)}")
        
        # Create a copy of the DataFrame to preserve all columns
        df_copy = df.copy()
        
        # Ensure the signal column exists
        if signal_column not in df_copy.columns:
            raise ValueError(f"Signal column '{signal_column}' not found in DataFrame")
        
        # Create the appropriate signal column (don't overwrite if exists)  (buy_signal or sell_signal)
        signal_col_name = f"{condition_type}_signal"
        if signal_col_name not in df_copy.columns:
            df_copy[signal_col_name] = 0
        
        # Convert threshold to float if it's a Decimal (from database NUMERIC columns)
        if isinstance(threshold, Decimal):
            threshold = float(threshold)
            print(f"Converted Decimal threshold to float: {threshold}")
        
        # Apply the condition based on operator
        if operator == '>':
            condition = df_copy[signal_column] > threshold
        elif operator == '<':
            condition = df_copy[signal_column] < threshold
        elif operator == '>=':
            condition = df_copy[signal_column] >= threshold
        elif operator == '<=':
            condition = df_copy[signal_column] <= threshold
        elif operator == '==':
            condition = df_copy[signal_column] == threshold
        elif operator == '!=':
            condition = df_copy[signal_column] != threshold
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        # Set signal where condition is true
        df_copy.loc[condition, signal_col_name] = 1
        
        signal_count = df_copy[signal_col_name].sum()
        print(f"Generated {signal_count} {condition_type} signals")
        print(f"Output DataFrame columns: {list(df_copy.columns)}")
        
        return df_copy
        
    except Exception as e:
        print(f"Error applying condition to signal: {e}")
        print(traceback.format_exc())
        raise Exception(f"Failed to apply condition to signal: {str(e)}")


def check_signal_column_exists(df: pd.DataFrame, signal_name: str) -> bool:
    """
    Check if a signal column already exists in the DataFrame
    
    Args:
        df (pd.DataFrame): Input DataFrame
        signal_name (str): Name of the signal to check
        
    Returns:
        bool: True if signal column exists, False otherwise
    """
    # Check for exact column name or common variations
    possible_names = [
        signal_name,
        signal_name.lower(),
        signal_name.upper(),
        signal_name.replace(' ', '_'),
        signal_name.replace(' ', '_').lower(),
        signal_name.replace('_', ' '),
    ]
    
    for col_name in possible_names:
        if col_name in df.columns:
            print(f"Found existing signal column: {col_name}")
            return True
    
    return False

def run_backtest_with_prepared_signals(
    df: pd.DataFrame,
    network: str,
    token_symbol: str,
    timeframe: str,
    time_start: str,
    time_end: str,
    buy_signal_name: str = None,
    sell_signal_name: str = None
):
    """
    Run backtest with a DataFrame that already has buy_signal and sell_signal columns
    
    Args:
        df (pd.DataFrame): DataFrame with OHLC data and buy_signal/sell_signal columns
        network (str): Network name
        token_symbol (str): Token symbol  
        timeframe (str): Timeframe used
        time_start (str): Start time
        time_end (str): End time
        buy_signal_name (str): Name of buy signal for display
        sell_signal_name (str): Name of sell signal for display
        
    Returns:
        dict: Backtest results with trading statistics and plotly figure
    """
    print(f"Running backtest with prepared signals...")
    print(f"DataFrame shape: {df.shape}")
    print(f"Buy signal name: {buy_signal_name}")
    print(f"Sell signal name: {sell_signal_name}")
    
    # Verify required columns exist
    required_columns = ['buy_signal', 'sell_signal', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise Exception(f"Missing required columns: {missing_columns}")
    
    # Check signal counts
    buy_signals = df['buy_signal'].sum()
    sell_signals = df['sell_signal'].sum()
    print(f"Buy signals: {buy_signals}")
    print(f"Sell signals: {sell_signals}")
    
    if buy_signals == 0 and sell_signals == 0:
        return {
            "error": "No trading signals found in DataFrame",
            "buy_signals": 0,
            "sell_signals": 0,
            "trading_stats": {}
        }
    
    try:
        # Convert datetime if needed
        if 'datetime' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Calculate trading stats
        stats = calculate_trading_stats(df, ['buy_signal'], ['sell_signal'])
        
        # Create indicator info for plotting
        buy_indicator_info = {
            'name': buy_signal_name or "Buy Signal",
            'path': 'database',
            'code': 'stored_in_database',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new_columns': ['buy_signal']
        }
        
        sell_indicator_info = {
            'name': sell_signal_name or "Sell Signal",
            'path': 'database',
            'code': 'stored_in_database',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'new_columns': ['sell_signal']
        }
        
        # Generate plot
        fig = plot_backtest_results(
            df=df,
            buy_indicator_info=buy_indicator_info,
            sell_indicator_info=sell_indicator_info,
            buy_signal_columns=['buy_signal'],
            sell_signal_columns=['sell_signal'],
            title=None,   # will be generated in the code
            network=network,
            pool=None,  # We don't have pool info here
            timeframe=timeframe,
            aggregate=1
        )
        
        # Format the result
        result = {
            "success": True,
            "buy_signals": int(buy_signals),
            "sell_signals": int(sell_signals),
            "data_points": len(df),
            "timeframe": timeframe,
            "time_range": {"start": time_start, "end": time_end},
            "trading_stats": stats,
            "buy_indicator_info": {
                "name": buy_signal_name or "Buy Signal",
                "signals_generated": int(buy_signals)
            },
            "sell_indicator_info": {
                "name": sell_signal_name or "Sell Signal", 
                "signals_generated": int(sell_signals)
            },
            "plotly_figure": fig.to_json() if fig else None
        }
        
        print("Backtest completed successfully")
        return result
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "buy_signals": int(buy_signals) if 'buy_signals' in locals() else 0,
            "sell_signals": int(sell_signals) if 'sell_signals' in locals() else 0
        } 