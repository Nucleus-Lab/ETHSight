import sys
import os
import time
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Optional, Tuple, AsyncGenerator

# Add the backtest_utils directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.database.signal import get_signal_by_id, get_signal_calculation_code, signal_has_calculation_code, update_signal_calculation_code
from web3 import Web3
import json
from dotenv import load_dotenv

# Import simplified interface functions
from backtest_utils.strategy_interface import (
    generate_signal_calculation_code_from_prompt,
    apply_signal_calculation_code,
    apply_condition_to_signal,
)

# Import GeckoTerminal API
from backtest_utils.geckoterminal_backtracker.api.gecko_api import GeckoTerminalAPI
from backtest_utils.geckoterminal_backtracker.analysis.indicator_backtester import (
    calculate_trading_stats,
    plot_backtest_results
)

# Initialize GeckoTerminal API
gecko_api = GeckoTerminalAPI()

# Load environment variables
load_dotenv()

# Environment variables
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
BSC_TESTNET_RPC_URL = os.getenv('BSC_TESTNET_RPC_URL')

# Initialize Web3
bsc_testnet = Web3(Web3.HTTPProvider(BSC_TESTNET_RPC_URL))
assert bsc_testnet.is_connected(), "Failed to connect to BSC Testnet"

# Token addresses for BSC Testnet
WBNB = Web3.to_checksum_address('0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd')  # Testnet WBNB
CAKE = Web3.to_checksum_address('0xFa60D973F7642B748046464e165A65B7323b0DEE')  # Testnet CAKE

def swap_tokens(amount_in: float, token_in: str, token_out: str, slippage: float = 0.5) -> dict:
    """
    Execute a token swap on PancakeSwap
    
    Args:
        amount_in: Amount of input token to swap
        token_in: Input token address
        token_out: Output token address
        slippage: Slippage tolerance in percentage (default 0.5%)
        
    Returns:
        dict: Transaction details including hash and status
    """
    try:
        # PancakeSwap router address on BSC Testnet
        router_address = Web3.to_checksum_address("0x9a489505a00cE272eAa5e07Dba6491314CaE3796")
        
        # Load router ABI
        with open('abis/PancakeSwapSmartRouter.json') as f:
            router_abi = json.load(f)
        router = bsc_testnet.eth.contract(address=router_address, abi=router_abi)
        
        # Convert amount to Wei
        amount_in_wei = bsc_testnet.to_wei(amount_in, 'ether')
        
        # Calculate minimum amount out based on slippage
        amount_out_min = 0  # For testing, set to 0. In production, should calculate based on slippage
        
        # Set deadline 10 minutes from now
        deadline = int(time.time()) + 60 * 10
        
        # Prepare swap parameters
        params = {
            'tokenIn': Web3.to_checksum_address(token_in),
            'tokenOut': Web3.to_checksum_address(token_out),
            'fee': 2500,  # 0.25% fee tier
            'recipient': WALLET_ADDRESS,
            'amountIn': amount_in_wei,
            'amountOutMinimum': amount_out_min,
            'sqrtPriceLimitX96': 0  # No price limit
        }
        
        # Build transaction
        txn = router.functions.exactInputSingle(params).build_transaction({
            'from': WALLET_ADDRESS,
            'value': amount_in_wei if token_in.lower() == WBNB.lower() else 0,  # Send BNB only if swapping from BNB
            'gas': 300000,
            'gasPrice': bsc_testnet.to_wei('5', 'gwei'),
            'nonce': bsc_testnet.eth.get_transaction_count(WALLET_ADDRESS),
            'chainId': 97  # BSC Testnet chain ID
        })
        
        # Estimate gas
        gas = bsc_testnet.eth.estimate_gas({
            'from': WALLET_ADDRESS, 
            'to': router_address, 
            'data': txn['data'], 
            'value': amount_in_wei if token_in.lower() == WBNB.lower() else 0
        })
        txn['gas'] = gas
        
        print(f"Estimated gas: {gas}")
        
        # Sign and send transaction
        signed_txn = bsc_testnet.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
        tx_hash = bsc_testnet.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        # Wait for transaction receipt
        receipt = bsc_testnet.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            'status': 'success',
            'transaction_hash': tx_hash.hex(),
            'gas_used': receipt['gasUsed'],
            'status_code': receipt['status']
        }
        
    except Exception as e:
        print(f"Error executing swap: {str(e)}")
        raise Exception(f"Failed to execute swap: {str(e)}")

def get_or_generate_signal_calculation_code(db: Session, signal_id: int) -> str:
    """Get signal calculation code from database or generate if not exists (decoupled approach)"""
    # Check if signal has calculation code in database
    if signal_has_calculation_code(db, signal_id):
        print(f"✅ Using cached signal calculation code for signal {signal_id}")
        return get_signal_calculation_code(db, signal_id)
    
    # Generate new calculation code if not in database
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    print(f"🔄 Generating new signal calculation code for signal {signal_id}: {signal.signal_name}")
    
    try:
        # Generate the signal calculation code (decoupled from buy/sell logic)
        code = generate_signal_calculation_code_from_prompt(
            signal_description=signal.signal_description,
            signal_name=signal.signal_name
        )
        
        # Store the calculation code in database
        update_signal_calculation_code(db, signal_id, code)
        
        print(f"✅ Generated and cached signal calculation code for signal {signal_id}")
        return code
        
    except Exception as e:
        print(f"❌ Error generating signal calculation code for signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate signal calculation code: {str(e)}")


def prepare_signal_with_condition(df, signal_id: int, operator: str, threshold: float, condition_type: str, db: Session):
    """
    Prepare a signal by calculating signal values and applying conditions (decoupled approach)
    
    Args:
        df: DataFrame with OHLC data
        signal_id: Signal ID from database
        operator: Comparison operator
        threshold: Threshold value
        condition_type: 'buy' or 'sell'
        db: Database session
        
    Returns:
        tuple: (df_with_signals, signal_column_name)
    """
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    
    signal_name = signal.signal_name
    
    print(f"🔄 Preparing {condition_type} signal: {signal_name} {operator} {threshold}")
    
    # Make a copy of the DataFrame to preserve existing columns
    df_copy = df.copy()
    
    # Step 1: Get or generate signal calculation code (AI will check for existing columns)
    signal_calc_code = get_or_generate_signal_calculation_code(db, signal_id)
    
    # Step 2: Apply signal calculation code (AI will use existing column if found, or calculate new one)
    df_with_signal, signal_column = apply_signal_calculation_code(df_copy, signal_calc_code, signal_name)
    print(f"   🎯 Signal column ready: {signal_column}")
    
    # Step 3: Apply condition to generate buy/sell signals
    df_with_signal = apply_condition_to_signal(df_with_signal, signal_column, operator, threshold, condition_type)
    
    # Step 4: Verify all columns were preserved
    print(f"   📋 DataFrame columns after signal preparation: {list(df_with_signal.columns)}")
    
    return df_with_signal, signal_column

class TradeMonitor:
    def __init__(self, 
                 db: Session,
                 strategy_id: int,
                 network: str,
                 pool_address: str,
                 buy_signal_id: int,
                 buy_operator: str,
                 buy_threshold: float,
                 sell_signal_id: int,
                 sell_operator: str,
                 sell_threshold: float,
                 position_size: float):
        """
        Initialize trade monitor
        """
        self.db = db
        self.strategy_id = strategy_id
        self.network = network
        self.pool_address = pool_address
        self.buy_signal_id = buy_signal_id
        self.buy_operator = buy_operator
        self.buy_threshold = buy_threshold
        self.sell_signal_id = sell_signal_id
        self.sell_operator = sell_operator
        self.sell_threshold = sell_threshold
        self.position_size = position_size
        
        # Trading state
        self.current_position = 0
        self.entry_price = 0
        self.total_pnl = 0
        self.trades = []
        
        # Data storage
        self.df = pd.DataFrame()
        self.last_update = None
        self.is_monitoring = False
        self._force_stop = False  # Emergency stop flag
        
        # Get signal calculation code
        self.buy_signal_code = get_signal_calculation_code(db, buy_signal_id)
        self.sell_signal_code = get_signal_calculation_code(db, sell_signal_id)
        
        # Signal info for plotting
        self.buy_signal_info = {
            'name': get_signal_by_id(db, buy_signal_id).signal_name,
            'new_columns': []  # Will be populated when signals are calculated
        }
        self.sell_signal_info = {
            'name': get_signal_by_id(db, sell_signal_id).signal_name,
            'new_columns': []  # Will be populated when signals are calculated
        }
    
    async def initialize_dataframe_async(self) -> AsyncGenerator[Dict, None]:
        """Initialize DataFrame with historical data with progress updates"""
        
        # Step 1: Fetch data
        yield {
            'status': 'initializing',
            'message': 'Fetching historical data...',
            'progress': 25
        }
        
        fetch_start = time.time()
        df = gecko_api.get_ohlc(
            network=self.network,
            pool_address=self.pool_address,
            timeframe='minute',
            aggregate=1,
            limit=100
        )
        fetch_end = time.time()
        print(f"⏱️ [TIMING] Initial data fetch: {fetch_end - fetch_start:.3f} seconds", flush=True)
        
        # Step 2: Process timestamps
        yield {
            'status': 'initializing',
            'message': 'Processing timestamps...',
            'progress': 50
        }
        
        timestamp_start = time.time()
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        timestamp_end = time.time()
        print(f"⏱️ [TIMING] Timestamp processing: {timestamp_end - timestamp_start:.3f} seconds", flush=True)
        
        if df.empty:
            raise Exception("Failed to fetch initial data")
        
        sort_start = time.time()
        self.df = df.sort_values('datetime')
        self.last_update = self.df['datetime'].max()
        sort_end = time.time()
        print(f"⏱️ [TIMING] Data sorting: {sort_end - sort_start:.3f} seconds", flush=True)
                
        print(f"✅ Done initializing dataframe for strategy {self.strategy_id}")
        
        # Calculate initial signals for plotting context (but no trading signals yet)
        yield {
            'status': 'initializing',
            'message': 'Calculating initial indicators for chart...',
            'progress': 75
        }
        
        initial_signals_start = time.time()
        self._calculate_initial_indicators()
        initial_signals_end = time.time()
        print(f"⏱️ [TIMING] Initial indicators calculation: {initial_signals_end - initial_signals_start:.3f} seconds", flush=True)
        
        yield {
            'status': 'initializing',
            'message': 'Setup complete, ready for live trading...',
            'progress': 90
        }
    
    def _calculate_initial_indicators(self):
        """Calculate indicators for the initial dataframe (for plotting only, no trading signals)"""
        if self.df.empty:
            return
            
        # Calculate buy signal indicators for plotting
        self.df, buy_signal_column = apply_signal_calculation_code(
            self.df, 
            self.buy_signal_code,
            self.buy_signal_info['name']
        )
        
        # Calculate sell signal indicators for plotting  
        self.df, sell_signal_column = apply_signal_calculation_code(
            self.df,
            self.sell_signal_code,
            self.sell_signal_info['name']
        )
        
        # Initialize trading signal columns (but don't set any signals for historical data)
        self.df['buy_signal'] = 0
        self.df['sell_signal'] = 0
        
        # Store column names for later use
        self.buy_signal_info['column'] = buy_signal_column
        self.sell_signal_info['column'] = sell_signal_column
        
        print(f"✅ Initial indicators calculated: {buy_signal_column}, {sell_signal_column}")
    
    def _calculate_signals(self) -> Tuple[List[str], List[str]]:
        """Calculate indicators for new data and trading signals for latest data only"""
        if self.df.empty:
            return [], []
        
        # Get stored column names from initialization
        buy_signal_column = self.buy_signal_info['name']
        sell_signal_column = self.sell_signal_info['name']
        
        # Only recalculate indicators for the latest row (most efficient)
        signals_calc_start = time.time()
        
        # Create a temporary dataframe with just the latest row for indicator calculation
        latest_row_df = self.df.tail(20).copy()  # Take last 20 rows for context (some indicators need history)
        
        # Calculate buy indicator for the latest rows
        latest_row_df, _ = apply_signal_calculation_code(
            latest_row_df, 
            self.buy_signal_code,
            self.buy_signal_info['name']
        )
        
        # Calculate sell indicator for the latest rows  
        latest_row_df, _ = apply_signal_calculation_code(
            latest_row_df,
            self.sell_signal_code,
            self.sell_signal_info['name']
        )
        
        # Update the main dataframe with the new indicator values for the latest row
        latest_idx = self.df.index[-1]
        if buy_signal_column in latest_row_df.columns:
            self.df.loc[latest_idx, buy_signal_column] = latest_row_df[buy_signal_column].iloc[-1]
        if sell_signal_column in latest_row_df.columns:
            self.df.loc[latest_idx, sell_signal_column] = latest_row_df[sell_signal_column].iloc[-1]
            
        signals_calc_end = time.time()
        print(f"⏱️ [TIMING] Indicator calculation (latest row): {signals_calc_end - signals_calc_start:.3f} seconds", flush=True)
        
        # Apply conditions to generate actual buy/sell signals ONLY for the latest data
        # (since we can only trade on new data, not historical data)
        buy_condition_start = time.time()
        
        # Initialize buy_signal column if it doesn't exist
        if 'buy_signal' not in self.df.columns:
            self.df['buy_signal'] = 0
        
        # Only calculate trading signals for the latest row (where we can actually trade)
        latest_idx = self.df.index[-1]
        latest_row = self.df.iloc[-1]
        
        # Apply buy condition only to latest data
        if buy_signal_column in latest_row and not pd.isna(latest_row[buy_signal_column]):
            if self.buy_operator == '>':
                buy_signal_value = 1 if latest_row[buy_signal_column] > self.buy_threshold else 0
            elif self.buy_operator == '<':
                buy_signal_value = 1 if latest_row[buy_signal_column] < self.buy_threshold else 0
            elif self.buy_operator == '>=':
                buy_signal_value = 1 if latest_row[buy_signal_column] >= self.buy_threshold else 0
            elif self.buy_operator == '<=':
                buy_signal_value = 1 if latest_row[buy_signal_column] <= self.buy_threshold else 0
            elif self.buy_operator == '==':
                buy_signal_value = 1 if latest_row[buy_signal_column] == self.buy_threshold else 0
            else:
                buy_signal_value = 0
            
            self.df.loc[latest_idx, 'buy_signal'] = buy_signal_value
            
        buy_condition_end = time.time()
        print(f"⏱️ [TIMING] Buy condition (latest row only): {buy_condition_end - buy_condition_start:.3f} seconds", flush=True)
        
        sell_condition_start = time.time()
        
        # Initialize sell_signal column if it doesn't exist
        if 'sell_signal' not in self.df.columns:
            self.df['sell_signal'] = 0
            
        # Apply sell condition only to latest data
        if sell_signal_column in latest_row and not pd.isna(latest_row[sell_signal_column]):
            if self.sell_operator == '>':
                sell_signal_value = 1 if latest_row[sell_signal_column] > self.sell_threshold else 0
            elif self.sell_operator == '<':
                sell_signal_value = 1 if latest_row[sell_signal_column] < self.sell_threshold else 0
            elif self.sell_operator == '>=':
                sell_signal_value = 1 if latest_row[sell_signal_column] >= self.sell_threshold else 0
            elif self.sell_operator == '<=':
                sell_signal_value = 1 if latest_row[sell_signal_column] <= self.sell_threshold else 0
            elif self.sell_operator == '==':
                sell_signal_value = 1 if latest_row[sell_signal_column] == self.sell_threshold else 0
            else:
                sell_signal_value = 0
                
            self.df.loc[latest_idx, 'sell_signal'] = sell_signal_value
            
        sell_condition_end = time.time()
        print(f"⏱️ [TIMING] Sell condition (latest row only): {sell_condition_end - sell_condition_start:.3f} seconds", flush=True)
        
        total_signals_time = sell_condition_end - signals_calc_start
        print(f"⏱️ [TIMING] 📊 TOTAL SIGNAL CALCULATION (optimized): {total_signals_time:.3f} seconds", flush=True)
        print(f"⏱️ [SIGNALS] Latest row - Buy: {self.df.loc[latest_idx, 'buy_signal']}, Sell: {self.df.loc[latest_idx, 'sell_signal']}", flush=True)
        
        return [buy_signal_column], [sell_signal_column]
    
    def _check_signals(self, row: pd.Series) -> Optional[Dict]:
        """Check for buy/sell signals and execute trades"""
        trade_executed = None
        current_price = row['close']
        
        # Check buy signal
        if row['buy_signal'] == 1 and self.current_position == 0:
            self.current_position = 1
            self.entry_price = current_price
            trade_executed = {
                'type': 'buy',
                'price': current_price,
                'timestamp': row['datetime'].isoformat() if hasattr(row['datetime'], 'isoformat') else str(row['datetime']),
                'size': self.position_size
            }
            print(f"🔵 Buy Signal: Price={current_price}")
            
        # Check sell signal
        elif row['sell_signal'] == 1 and self.current_position > 0:
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            self.total_pnl += pnl_pct
            
            trade_executed = {
                'type': 'sell',
                'price': current_price,
                'timestamp': row['datetime'].isoformat() if hasattr(row['datetime'], 'isoformat') else str(row['datetime']),
                'size': self.position_size,
                'pnl_pct': pnl_pct
            }
            
            self.trades.append({
                'buy_time': self.entry_price,
                'sell_time': current_price,
                'buy_price': self.entry_price,
                'sell_price': current_price,
                'profit': pnl_pct
            })
            
            self.current_position = 0
            print(f"🔴 Sell Signal: Price={current_price}, PnL={pnl_pct:.2f}%")
            
        return trade_executed
    
    async def monitor_and_trade(self) -> AsyncGenerator[Dict, None]:
        """
        Monitor price and generate trading signals
        Yields updated plot and trading stats
        """
        self.is_monitoring = True
        
        # Yield initialization status
        yield {
            'status': 'initializing',
            'message': 'Starting trade monitor...',
            'progress': 0
        }
        
        # Initialize dataframe with progress updates
        init_start_time = time.time()
        try:
            async for progress_update in self.initialize_dataframe_async():
                # Check for stop signal during initialization
                if not self.is_monitoring or self._force_stop:
                    print(f"🛑 Monitor stopped during initialization for strategy {self.strategy_id}", flush=True)
                    return
                yield progress_update
        except Exception as e:
            print(f"Error during initialization: {str(e)}")
            print(traceback.format_exc())
            yield {
                'status': 'error',
                'error': f"Initialization failed: {str(e)}"
            }
            return
        init_end_time = time.time()
        print(f"⏱️ [TIMING] INITIALIZATION took: {init_end_time - init_start_time:.3f} seconds", flush=True)
        
        # Final stop check after initialization
        if not self.is_monitoring or self._force_stop:
            print(f"🛑 Monitor stopped after initialization for strategy {self.strategy_id}", flush=True)
            return
        
        # Yield ready status
        yield {
            'status': 'ready',
            'message': 'Trade monitor ready, starting live trading...',
            'progress': 100
        }
        
        # Yield initial results immediately using existing data
        print("[TRADE MONITOR] Generating initial plot with existing data...", flush=True)
        initial_results_start_time = time.time()
        try:
            # Check for stop before processing initial results
            if not self.is_monitoring or self._force_stop:
                print(f"🛑 Monitor stopped before initial results for strategy {self.strategy_id}", flush=True)
                return
                
            # Use data we already have from initialization
            initial_stats_start = time.time()
            initial_stats = calculate_trading_stats(self.df, [], [])
            initial_stats_end = time.time()
            print(f"⏱️ [TIMING] Initial stats calculation: {initial_stats_end - initial_stats_start:.3f} seconds", flush=True)
            
            # Check for stop after stats calculation
            if not self.is_monitoring or self._force_stop:
                print(f"🛑 Monitor stopped during initial stats calculation for strategy {self.strategy_id}", flush=True)
                return
            
            initial_plot_start = time.time()
            initial_fig = plot_backtest_results(
                df=self.df,
                buy_indicator_info=self.buy_signal_info,
                sell_indicator_info=self.sell_signal_info,
                buy_signal_columns=[],  # no buy and sell signals yet
                sell_signal_columns=[],  # no buy and sell signals yet
                network=self.network,
                pool=self.pool_address
            )
            initial_plot_end = time.time()
            print(f"⏱️ [TIMING] Initial plot generation: {initial_plot_end - initial_plot_start:.3f} seconds", flush=True)
            
            # Check for stop after plot generation
            if not self.is_monitoring or self._force_stop:
                print(f"🛑 Monitor stopped during initial plot generation for strategy {self.strategy_id}", flush=True)
                return
            
            # Yield initial results immediately
            yield {
                'status': 'update',
                'timestamp': self.last_update.isoformat(),
                'price': float(self.df['close'].iloc[-1]),
                'trade_executed': None,
                'current_position': self.current_position,
                'total_pnl': self.total_pnl,
                'trading_stats': initial_stats,
                'fig': initial_fig
            }
            initial_results_end_time = time.time()
            print(f"⏱️ [TIMING] INITIAL RESULTS total: {initial_results_end_time - initial_results_start_time:.3f} seconds", flush=True)
            print("[TRADE MONITOR] Initial results yielded successfully!", flush=True)
            
        except Exception as e:
            print(f"Error generating initial results: {str(e)}", flush=True)
            traceback.print_exc()
            # Continue anyway
        
        while self.is_monitoring and not self._force_stop:
            loop_start_time = time.time()
            print(f"🔄 [LOOP START] Strategy {self.strategy_id} - is_monitoring: {self.is_monitoring}, _force_stop: {self._force_stop}, monitor ID: {id(self)}", flush=True)
            
            # Double-check monitoring status at start of each loop
            if not self.is_monitoring or self._force_stop:
                print(f"🛑 Monitor stop signal detected for strategy {self.strategy_id} (is_monitoring: {self.is_monitoring}, _force_stop: {self._force_stop})", flush=True)
                break
                
            try:
                # Fetch latest data
                fetch_start_time = time.time()
                new_data = gecko_api.get_ohlc(
                    network=self.network,
                    pool_address=self.pool_address,
                    timeframe='minute',
                    aggregate=1,
                    limit=1
                )
                
                print(f"🔥 New data: {new_data}")
                
                # Check for stop after data fetch
                if not self.is_monitoring or self._force_stop:
                    print(f"🛑 Monitor stopped after data fetch for strategy {self.strategy_id}", flush=True)
                    break
                
                # TODO: fix this (supposedly we only need timestamp)
                new_data['datetime'] = pd.to_datetime(new_data['timestamp'], unit='s')
                new_data = new_data.sort_values('datetime')
                fetch_end_time = time.time()
                print(f"⏱️ [TIMING] Data fetch: {fetch_end_time - fetch_start_time:.3f} seconds", flush=True)
                
                if not new_data.empty:
                    latest_datetime = new_data['datetime'].iloc[-1]
                    
                    # Only process if we have new data, or new data is at the same time as the last update
                    if self.last_update is None or latest_datetime >= self.last_update:
                        # Update or append new data (don't drop duplicates, update with latest values)
                        data_prep_start = time.time()
                        
                        # Check if this timestamp already exists
                        existing_mask = self.df['datetime'] == latest_datetime
                        if existing_mask.any():
                            # Update existing row with latest values
                            print(f"⏱️ [DATA] Updating existing row for {latest_datetime}", flush=True)
                            self.df.loc[existing_mask, ['open', 'high', 'low', 'close', 'volume']] = new_data[['open', 'high', 'low', 'close', 'volume']].iloc[0]
                        else:
                            # Append new row
                            print(f"⏱️ [DATA] Adding new row for {latest_datetime}", flush=True)
                            self.df = pd.concat([self.df, new_data])
                        
                        # Keep last 100 points and sort
                        self.df = self.df.sort_values('datetime').tail(100)
                        self.last_update = latest_datetime
                        data_prep_end = time.time()
                        print(f"⏱️ [TIMING] Data preparation: {data_prep_end - data_prep_start:.3f} seconds", flush=True)
                        
                        print("[TRADE MONITOR] New data fetched. Processing update...", flush=True)
                        
                        # Check for stop before processing update
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped before processing update for strategy {self.strategy_id}", flush=True)
                            break
                        
                        # Yield status update before heavy computation
                        yield {
                            'status': 'processing',
                            'message': 'Processing new data and calculating signals...',
                            'timestamp': latest_datetime.isoformat(),
                            'price': float(new_data['close'].iloc[-1])
                        }
                        
                        # Calculate signals (HEAVY OPERATION)
                        print("[TRADE MONITOR] Calculating signals...", flush=True)
                        
                        # Check for stop before signals calculation
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped before signals calculation for strategy {self.strategy_id}", flush=True)
                            break
                        
                        yield {
                            'status': 'processing',
                            'message': 'Calculating trading signals...',
                            'timestamp': latest_datetime.isoformat(),
                            'price': float(new_data['close'].iloc[-1])
                        }
                        signals_start_time = time.time()
                        buy_cols, sell_cols = self._calculate_signals()
                        signals_end_time = time.time()
                        print(f"⏱️ [TIMING] Signal calculation: {signals_end_time - signals_start_time:.3f} seconds", flush=True)
                        
                        # Check for stop after signals calculation
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped after signals calculation for strategy {self.strategy_id}", flush=True)
                            break
                        
                        print("[TRADE MONITOR] Signals calculated. Checking for signals...", flush=True)
                        # Check for signals in new data
                        check_signals_start = time.time()
                        trade = self._check_signals(self.df.iloc[-1])
                        check_signals_end = time.time()
                        print(f"⏱️ [TIMING] Signal checking: {check_signals_end - check_signals_start:.3f} seconds", flush=True)
                        
                        # Check for stop after signal checking
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped after signal checking for strategy {self.strategy_id}", flush=True)
                            break
                        
                        print("[TRADE MONITOR] Signals checked. Calculating trading stats...", flush=True)
                        yield {
                            'status': 'processing',
                            'message': 'Calculating trading statistics...',
                            'timestamp': latest_datetime.isoformat(),
                            'price': float(new_data['close'].iloc[-1])
                        }
                        # Calculate trading stats (HEAVY OPERATION)
                        stats_start_time = time.time()
                        stats = calculate_trading_stats(self.df, buy_cols, sell_cols)
                        stats_end_time = time.time()
                        print(f"⏱️ [TIMING] Trading stats calculation: {stats_end_time - stats_start_time:.3f} seconds", flush=True)
                        
                        # Check for stop after stats calculation
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped after stats calculation for strategy {self.strategy_id}", flush=True)
                            break
                        
                        print("[TRADE MONITOR] Trading stats calculated. Generating plot...", flush=True)
                        yield {
                            'status': 'processing',
                            'message': 'Generating updated chart...',
                            'timestamp': latest_datetime.isoformat(),
                            'price': float(new_data['close'].iloc[-1])
                        }
                        # Generate plot (HEAVY OPERATION)
                        plot_start_time = time.time()
                        fig = plot_backtest_results(
                            df=self.df,
                            buy_indicator_info=self.buy_signal_info,
                            sell_indicator_info=self.sell_signal_info,
                            buy_signal_columns=['buy_signal'],
                            sell_signal_columns=['sell_signal'],
                            network=self.network,
                            pool=self.pool_address
                        )
                        plot_end_time = time.time()
                        print(f"⏱️ [TIMING] Plot generation: {plot_end_time - plot_start_time:.3f} seconds", flush=True)
                        
                        # Check for stop after plot generation
                        if not self.is_monitoring or self._force_stop:
                            print(f"🛑 Monitor stopped after plot generation for strategy {self.strategy_id}", flush=True)
                            break
                        
                        print("[TRADE MONITOR] Plot generated. Yielding updated results...", flush=True)
                        
                        # Yield updated results
                        yield {
                            'status': 'update',
                            'timestamp': latest_datetime.isoformat(),
                            'price': float(new_data['close'].iloc[-1]),
                            'trade_executed': trade,
                            'current_position': self.current_position,
                            'total_pnl': self.total_pnl,
                            'trading_stats': stats,
                            'fig': fig
                        }
                        
                        loop_processing_end = time.time()
                        total_processing_time = loop_processing_end - (fetch_start_time)
                        print(f"⏱️ [TIMING] 🔥 TOTAL PROCESSING TIME: {total_processing_time:.3f} seconds", flush=True)
                        print(f"⏱️ [TIMING] ⚡ Breakdown - Fetch: {fetch_end_time - fetch_start_time:.3f}s, " + 
                              f"Signals(optimized): {signals_end_time - signals_start_time:.3f}s, " +
                              f"Stats: {stats_end_time - stats_start_time:.3f}s, " +
                              f"Plot: {plot_end_time - plot_start_time:.3f}s", flush=True)
                
                # Wait for 5 seconds before next update (with interruption check)
                sleep_start = time.time()
                for i in range(50):  # Check every 0.1 seconds for stop signal
                    print(f"💤 [SLEEP CHECK] Strategy {self.strategy_id} - is_monitoring: {self.is_monitoring}, _force_stop: {self._force_stop}, sleep step: {i}", flush=True)
                    if not self.is_monitoring or self._force_stop:
                        print(f"🛑 Monitor stopped during sleep for strategy {self.strategy_id} (is_monitoring: {self.is_monitoring}, _force_stop: {self._force_stop})", flush=True)
                        return
                    await asyncio.sleep(0.1)
                sleep_end = time.time()
                print(f"😴 [SLEEP DONE] Strategy {self.strategy_id} completed 5s sleep", flush=True)
                
                loop_end_time = time.time()
                total_loop_time = loop_end_time - loop_start_time
                print(f"⏱️ [TIMING] 🔄 FULL LOOP CYCLE: {total_loop_time:.3f} seconds (including {sleep_end - sleep_start:.3f}s sleep)", flush=True)
                print("=" * 80, flush=True)
                
            except Exception as e:
                print(f"Error in trade monitor: {str(e)}")
                print(traceback.format_exc())
                yield {
                    'status': 'error',
                    'error': str(e)
                }
                await asyncio.sleep(5)  # Wait before retrying
        
        print(f"🏁 Monitor loop ended for strategy {self.strategy_id}. is_monitoring: {self.is_monitoring}", flush=True)
        
        # Send final stopped status with current data
        try:
            if not self.df.empty:
                # Calculate final stats and plot
                final_buy_cols, final_sell_cols = self._calculate_signals() if hasattr(self, 'df') and not self.df.empty else ([], [])
                final_stats = calculate_trading_stats(self.df, final_buy_cols, final_sell_cols)
                final_fig = plot_backtest_results(
                    df=self.df,
                    buy_indicator_info=self.buy_signal_info,
                    sell_indicator_info=self.sell_signal_info,
                    buy_signal_columns=['buy_signal'] if 'buy_signal' in self.df.columns else [],
                    sell_signal_columns=['sell_signal'] if 'sell_signal' in self.df.columns else [],
                    network=self.network,
                    pool=self.pool_address
                )
                
                yield {
                    'status': 'stopped',
                    'message': 'Trading stopped',
                    'timestamp': self.last_update.isoformat() if self.last_update else None,
                    'price': float(self.df['close'].iloc[-1]) if not self.df.empty else None,
                    'current_position': self.current_position,
                    'total_pnl': self.total_pnl,
                    'trading_stats': final_stats,
                    'fig': final_fig
                }
                print(f"📤 Sent final stopped status for strategy {self.strategy_id}", flush=True)
        except Exception as e:
            print(f"❌ Error sending final stopped status: {str(e)}", flush=True)
            # Send basic stopped status if there's an error
            yield {
                'status': 'stopped',
                'message': 'Trading stopped',
                'timestamp': self.last_update.isoformat() if self.last_update else None,
                'current_position': self.current_position,
                'total_pnl': self.total_pnl
            }
    
    def stop(self):
        """Stop the monitoring"""
        print(f"🛑 STOP called for strategy {self.strategy_id}. Current is_monitoring: {self.is_monitoring}", flush=True)
        print(f"🛑 Monitor object ID: {id(self)}", flush=True)
        self.is_monitoring = False
        self._force_stop = True  # Set emergency stop
        print(f"🛑 is_monitoring set to False and _force_stop set to True for strategy {self.strategy_id}. New values: is_monitoring={self.is_monitoring}, _force_stop={self._force_stop}", flush=True)
        print(f"🛑 After setting, monitor object ID: {id(self)}", flush=True)

# async def start_trade_monitor(
#     db: Session,
#     strategy_id: int,
#     network: str,
#     pool_address: str,
#     buy_signal_id: int,
#     buy_operator: str,
#     buy_threshold: float,
#     sell_signal_id: int,
#     sell_operator: str,
#     sell_threshold: float,
#     position_size: float
# ) -> AsyncGenerator[Dict, None]:
#     """
#     Start monitoring trades for a strategy
#     Returns an async generator that yields updates
#     """
#     monitor = TradeMonitor(
#         db=db,
#         strategy_id=strategy_id,
#         network=network,
#         pool_address=pool_address,
#         buy_signal_id=buy_signal_id,
#         buy_operator=buy_operator,
#         buy_threshold=buy_threshold,
#         sell_signal_id=sell_signal_id,
#         sell_operator=sell_operator,
#         sell_threshold=sell_threshold,
#         position_size=position_size
#     )
    
#     async for update in monitor.monitor_and_trade():
#         yield update