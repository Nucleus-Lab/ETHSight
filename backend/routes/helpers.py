import sys
import os
import time
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
        
        print("signal code", code)
        
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
    
    def initialize_dataframe(self) -> None:
        """Initialize DataFrame with historical data"""
        # Get last 100 data points for initial plotting
        df = gecko_api.get_ohlc(
            network=self.network,
            pool_address=self.pool_address,
            timeframe='minute',
            aggregate=1,
            limit=100
        )
        
        # TODO: fix this (supposedly we only need timestamp)
        df['datetime'] = pd.to_datetime(df['timestamp'])
        
        if df.empty:
            raise Exception("Failed to fetch initial data")
        
        self.df = df.sort_values('datetime')
        self.last_update = self.df['datetime'].max()
        
        # Calculate initial signals
        self._calculate_signals()
    
    def _calculate_signals(self) -> Tuple[List[str], List[str]]:
        """Calculate buy and sell signals"""
        if self.df.empty:
            return [], []
        
        # Calculate buy signals
        self.df, buy_signal_column = apply_signal_calculation_code(
            self.df, 
            self.buy_signal_code,
            self.buy_signal_info['name']
        )
        
        # Calculate sell signals
        self.df, sell_signal_column = apply_signal_calculation_code(
            self.df,
            self.sell_signal_code,
            self.sell_signal_info['name']
        )
        
        # Apply conditions to generate actual buy/sell signals
        self.df = apply_condition_to_signal(
            self.df,
            buy_signal_column,
            self.buy_operator,
            self.buy_threshold,
            'buy'
        )
        
        self.df = apply_condition_to_signal(
            self.df,
            sell_signal_column,
            self.sell_operator,
            self.sell_threshold,
            'sell'
        )
        
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
                'timestamp': row['datetime'],
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
                'timestamp': row['datetime'],
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
        self.initialize_dataframe()
        
        while self.is_monitoring:
            try:
                # Fetch latest data
                new_data = gecko_api.get_ohlc(
                    network=self.network,
                    pool_address=self.pool_address,
                    timeframe='minute',
                    aggregate=1,
                    limit=1
                )
                
                # TODO: fix this (supposedly we only need timestamp)
                new_data['datetime'] = pd.to_datetime(new_data['timestamp'])
                new_data = new_data.sort_values('datetime')
                
                if not new_data.empty:
                    latest_datetime = new_data['datetime'].iloc[-1]
                    
                    # Only process if we have new data
                    if self.last_update is None or latest_datetime > self.last_update:
                        # Append new data
                        self.df = pd.concat([self.df, new_data]).drop_duplicates(subset=['datetime'])
                        self.df = self.df.sort_values('datetime').tail(100)  # Keep last 100 points
                        self.last_update = latest_datetime
                        
                        print("[TRADE MONITOR] New data fetched. Calculating signals...")
                        
                        # Calculate signals
                        buy_cols, sell_cols = self._calculate_signals()
                        
                        print("[TRADE MONITOR] Signals calculated. Checking for signals...")
                        
                        # Check for signals in new data
                        trade = self._check_signals(new_data.iloc[-1])
                        
                        print("[TRADE MONITOR] Signals checked. Calculating trading stats...")
                        
                        # Calculate trading stats
                        stats = calculate_trading_stats(self.df, buy_cols, sell_cols)
                        
                        print("[TRADE MONITOR] Trading stats calculated. Generating plot...")
                        
                        # Generate plot
                        fig = plot_backtest_results(
                            df=self.df,
                            buy_indicator_info=self.buy_signal_info,
                            sell_indicator_info=self.sell_signal_info,
                            buy_signal_columns=buy_cols,
                            sell_signal_columns=sell_cols,
                            network=self.network,
                            pool=self.pool_address
                        )
                        
                        print("[TRADE MONITOR] Plot generated. Yielding updated results...")
                        
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
                
                # Wait for 20 seconds before next update
                await asyncio.sleep(20)
                
            except Exception as e:
                print(f"Error in trade monitor: {str(e)}")
                yield {
                    'status': 'error',
                    'error': str(e)
                }
                await asyncio.sleep(20)  # Wait before retrying
    
    def stop(self):
        """Stop the monitoring"""
        self.is_monitoring = False

async def start_trade_monitor(
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
    position_size: float
) -> AsyncGenerator[Dict, None]:
    """
    Start monitoring trades for a strategy
    Returns an async generator that yields updates
    """
    monitor = TradeMonitor(
        db=db,
        strategy_id=strategy_id,
        network=network,
        pool_address=pool_address,
        buy_signal_id=buy_signal_id,
        buy_operator=buy_operator,
        buy_threshold=buy_threshold,
        sell_signal_id=sell_signal_id,
        sell_operator=sell_operator,
        sell_threshold=sell_threshold,
        position_size=position_size
    )
    
    async for update in monitor.monitor_and_trade():
        yield update