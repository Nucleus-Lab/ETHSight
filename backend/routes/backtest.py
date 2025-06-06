import sys
import os
import traceback
import pandas as pd

from typing import Dict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.database.signal import get_signal_by_id
from backend.database.user import get_user, create_user
from backend.database.strategy import create_strategy
from backend.database.backtest_history import create_backtest_history
from backend.routes.helpers import prepare_signal_with_condition

# Add the backtest_utils directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import simplified interface functions
from backtest_utils.strategy_interface import (
    run_backtest_with_prepared_signals,
    search_and_get_pool_address,
    fetch_ohlc_data
)

router = APIRouter()

class BacktestRequest(BaseModel):
    filter_signal_id: int
    buy_signal_id: int
    buy_operator: str
    buy_threshold: float
    sell_signal_id: int
    sell_operator: str
    sell_threshold: float
    position_size: float
    max_position_value: float
    time_range: Dict[str, str]
    network: str
    timeframe: str
    wallet_address: str

class SignalInfo(BaseModel):
    signal_id: int
    signal_name: str
    signal_description: str

class ConditionInfo(BaseModel):
    signal_info: SignalInfo
    operator: str
    threshold: float

class BacktestStrategy(BaseModel):
    filterSignal: SignalInfo
    buyCondition: ConditionInfo
    sellCondition: ConditionInfo
    positionSize: float
    maxPositionValue: float

class BacktestResults(BaseModel):
    trading_stats: dict
    data_points: int
    time_range: Dict[str, str]

class Signals(BaseModel):
    filter_signal: SignalInfo
    buy_signal: ConditionInfo
    sell_signal: ConditionInfo

class TokenInfo(BaseModel):
    name: str
    symbol: str
    contract_address: str

class Results(BaseModel):
    filterSignal: SignalInfo
    buySignal: SignalInfo
    sellSignal: SignalInfo

class BacktestResponse(BaseModel):
    status: str
    strategy_id: int
    fig: str          # json string
    backtest_results: BacktestResults
    signals: Signals
    token_info: TokenInfo
    
def get_signal_info(db: Session, signal_id: int) -> SignalInfo:
    """Helper function to get signal information from database"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal with id {signal_id} not found")
    
    return SignalInfo(
        signal_id=signal.signal_id,
        signal_name=signal.signal_name,
        signal_description=signal.signal_description
    )

@router.post("/strategy/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    """Run backtest with the given strategy"""
    print("type(strategy)", type(request))
    try:
        # Get or create user from wallet address
        user = get_user(db, request.wallet_address)
        if not user:
            user = create_user(db, request.wallet_address)
            print(f"Created new user for wallet: {request.wallet_address}")

        # Save strategy to database before running backtest
        saved_strategy = create_strategy(
            db=db,
            user_id=user.user_id,
            filter_signal_id=request.filter_signal_id,
            buy_condition_signal_id=request.buy_signal_id,
            buy_condition_operator=request.buy_operator,
            buy_condition_threshold=request.buy_threshold,
            sell_condition_signal_id=request.sell_signal_id,
            sell_condition_operator=request.sell_operator,
            sell_condition_threshold=request.sell_threshold,
            position_size=request.position_size,
            max_position_value=request.max_position_value
        )
        
        print(f"Strategy saved to database with ID: {saved_strategy.strategy_id}")
        
        # Get signal information for each signal in the strategy
        filter_signal = get_signal_info(db, request.filter_signal_id)
        buy_signal = get_signal_info(db, request.buy_signal_id)
        sell_signal = get_signal_info(db, request.sell_signal_id)
        
        print(f"Running backtest for strategy with signals:")
        print(f"Filter: {filter_signal.signal_name}")
        print(f"Buy: {buy_signal.signal_name}")
        print(f"Sell: {sell_signal.signal_name}")
        
        # Get token information from filter signal
        filter_signal_name = filter_signal.signal_name
        filter_signal_description = filter_signal.signal_description
        
        # For now, use hardcoded values - you can uncomment the line below to use the AI agent
        # token_name, token_symbol, token_contract_address = filter_token_info(filter_signal_name, filter_signal_description)
        token_name = "Ethereum"
        token_symbol = "ETH"
        token_contract_address = "0x0000000000000000000000000000000000000000"
        
        print(f"Token: {token_name} ({token_symbol})")
        
        # Step 1: Fetch OHLC data first to create DataFrame
        print("\n" + "="*60)
        print("📊 FETCHING MARKET DATA")
        print("="*60)
        try:
            # Search for pool address
            pool_address = search_and_get_pool_address(request.network, token_symbol)
            print(f"✅ Found pool address: {pool_address}")
        
            # Fetch OHLC data
            data_file_path = fetch_ohlc_data(
                network=request.network,
                pool_address=pool_address,
                timeframe=request.timeframe,
                time_start=request.time_range['start'],
                time_end=request.time_range['end']
            )
            
            # Read the CSV file to get the DataFrame
            print(f"📖 Reading data from: {data_file_path}")
            df = pd.read_csv(data_file_path)
            
            print(f"📋 DataFrame columns: {list(df.columns)}")
            
            # TODO: fix this (supposedly we only need timestamp)
            # Ensure datetime column exists and is properly formatted
            if 'datetime' not in df.columns:
                if 'timestamp' in df.columns:
                    df['datetime'] = pd.to_datetime(df['timestamp'])
                else:
                    # Create datetime from index if needed
                    df['datetime'] = pd.to_datetime(df.index)
            else:
                df['datetime'] = pd.to_datetime(df['datetime'])
                
            # Sort by datetime and check data
            df = df.sort_values('datetime')
            
            if df.empty:
                raise Exception("No data available for the specified time range")
                
            print(f"✅ Loaded {len(df)} data points")
            print(f"📊 DataFrame shape: {df.shape}")
            print(f"📅 Date range: {df['datetime'].min()} to {df['datetime'].max()}")
            
        except Exception as e:
            print(f"❌ Error fetching OHLC data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")
        
        # Step 2: Prepare DataFrame with signal calculations and conditions (DECOUPLED APPROACH)
        print("\n" + "="*60)
        print("🧮 PREPARING TRADING SIGNALS (DECOUPLED)")
        print("="*60)
        
        print("\n📈 Preparing buy signals...")
        df, buy_signal_column = prepare_signal_with_condition(
            df, 
            request.buy_signal_id, 
            request.buy_operator, 
            request.buy_threshold, 
            'buy', 
            db
        )
        
        print("\n📉 Preparing sell signals...")
        df, sell_signal_column = prepare_signal_with_condition(
            df, 
            request.sell_signal_id, 
            request.sell_operator, 
            request.sell_threshold, 
            'sell', 
            db
        )
        
        print(f"\n✅ Signal preparation completed:")
        print(f"   📈 Buy signal column: {buy_signal_column}")
        print(f"   📉 Sell signal column: {sell_signal_column}")
        
        # Validate signals were generated
        buy_signals = df['buy_signal'].sum()
        sell_signals = df['sell_signal'].sum()
        print(f"\n📊 Signal Statistics:")
        print(f"   📈 Total buy signals: {buy_signals}")
        print(f"   📉 Total sell signals: {sell_signals}")
        print(f"   📋 Data points: {len(df)}")
        
        if buy_signals == 0 and sell_signals == 0:
            print("\n❌ No trading signals generated!")
            return {
                "success": False,
                "error": "No trading signals were generated. Check your strategy conditions.",
                "buy_signals": 0,
                "sell_signals": 0,
                "data_points": len(df),
                "strategy_details": {
                    "buy_condition": f"{buy_signal.signal_name} {request.buy_operator} {request.buy_threshold}",
                    "sell_condition": f"{sell_signal.signal_name} {request.sell_operator} {request.sell_threshold}"
                }
            }
        
        # Set network and timeframe parameters
        network = request.network
        timeframe = request.timeframe
        
        # Step 3: Run backtest with the prepared signals (DECOUPLED APPROACH)
        print("\n" + "="*60) 
        print("🚀 RUNNING BACKTEST WITH DECOUPLED SIGNALS")
        print("="*60)
        
        backtest_result = run_backtest_with_prepared_signals(
            df=df,
            network=network,
            token_symbol=token_symbol,
            timeframe=timeframe,
            time_start=request.time_range['start'],
            time_end=request.time_range['end'],
            buy_signal_name=buy_signal.signal_name,
            sell_signal_name=sell_signal.signal_name
        )
        
        # Save backtest history to database
        try:
            backtest_history = create_backtest_history(
                db=db,
                user_id=user.user_id,
                strategy_id=saved_strategy.strategy_id,
                time_start=request.time_range['start'],
                time_end=request.time_range['end'],
                trading_stats=backtest_result['trading_stats'],
                data_points=backtest_result.get('data_points'),
                network=request.network,
                token_symbol=token_symbol,
                timeframe=request.timeframe
            )
            print(f"✅ Saved backtest history with ID: {backtest_history.backtest_id}")
        except Exception as e:
            print(f"⚠️  Warning: Failed to save backtest history: {e}")
            # Don't fail the entire request if history saving fails
        
        # Return comprehensive result with decoupled signal information
        return {
            "status": "success",
            "strategy_id": saved_strategy.strategy_id,
            "fig": backtest_result.get('plotly_figure'),
            "backtest_results": {
                "trading_stats": backtest_result.get('trading_stats', {}),
                "data_points": backtest_result.get('data_points'),
                "time_range": backtest_result.get('time_range')
            },
            "signals": {
                "filter_signal": {
                    "signal_id": filter_signal.signal_id,
                    "signal_name": filter_signal.signal_name,
                    "signal_description": filter_signal.signal_description,
                },
                "buy_signal": {
                    "signal_info": {
                        "signal_id": buy_signal.signal_id,
                        "signal_name": buy_signal.signal_name,
                        "signal_description": buy_signal.signal_description,
                    },
                    "operator": request.buy_operator,
                    "threshold": request.buy_threshold,
                },
                "sell_signal": {
                    "signal_info": {
                        "signal_id": sell_signal.signal_id,
                        "signal_name": sell_signal.signal_name,
                        "signal_description": sell_signal.signal_description,
                    },
                    "operator": request.sell_operator,
                    "threshold": request.sell_threshold,
                }
            },
            "token_info": {
                "name": token_name,
                "symbol": token_symbol,
                "contract_address": token_contract_address
            }
        }
        
    except Exception as e:
        print(f"Error running backtest: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to run backtest: {str(e)}")


@router.get("/backtest-history/user/{wallet_address}")
async def get_user_backtest_histories(wallet_address: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get backtest histories for a specific user"""
    try:
        # Get user from wallet address
        user = get_user(db, wallet_address)
        if not user:
            return {
                "status": "success",
                "backtest_histories": []
            }
        
        # Get backtest histories for the user
        from backend.database.backtest_history import get_backtest_histories_by_user
        histories = get_backtest_histories_by_user(db, user.user_id, limit)
        
        # Format backtest histories with strategy information
        formatted_histories = []
        for history in histories:
            try:
                # Get strategy information
                from backend.database.strategy import get_strategy_by_id
                strategy = get_strategy_by_id(db, history.strategy_id)
                
                if strategy:
                    # Get signal information for the strategy
                    filter_signal = get_signal_info(db, strategy.filter_signal_id)
                    buy_signal = get_signal_info(db, strategy.buy_condition_signal_id)
                    sell_signal = get_signal_info(db, strategy.sell_condition_signal_id)
                    
                    formatted_history = {
                        "backtest_id": history.backtest_id,
                        "strategy_id": history.strategy_id,
                        "time_start": history.time_start.isoformat(),
                        "time_end": history.time_end.isoformat(),
                        "total_return": history.total_return,
                        "avg_return": history.avg_return,
                        "win_rate": history.win_rate,
                        "total_trades": history.total_trades,
                        "profitable_trades": history.profitable_trades,
                        "data_points": history.data_points,
                        "network": history.network,
                        "token_symbol": history.token_symbol,
                        "timeframe": history.timeframe,
                        "created_at": history.created_at.isoformat(),
                        "strategy": {
                            "filter_condition": {
                                "signal_name": filter_signal.signal_name,
                                "signal_description": filter_signal.signal_description
                            },
                            "buy_condition": {
                                "signal_name": buy_signal.signal_name,
                                "signal_description": buy_signal.signal_description,
                                "operator": strategy.buy_condition_operator,
                                "threshold": strategy.buy_condition_threshold
                            },
                            "sell_condition": {
                                "signal_name": sell_signal.signal_name,
                                "signal_description": sell_signal.signal_description,
                                "operator": strategy.sell_condition_operator,
                                "threshold": strategy.sell_condition_threshold
                            },
                            "position_size": strategy.position_size,
                            "max_position_value": strategy.max_position_value
                        }
                    }
                    formatted_histories.append(formatted_history)
                
            except Exception as e:
                print(f"Error formatting backtest history {history.backtest_id}: {e}")
                continue
        
        print(f"Retrieved {len(formatted_histories)} backtest histories for user {user.user_id}")
        
        return {
            "status": "success",
            "backtest_histories": formatted_histories
        }
        
    except Exception as e:
        print(f"Error fetching backtest histories: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch backtest histories: {str(e)}") 

