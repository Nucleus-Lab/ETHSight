from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import (
    get_signal_by_id, 
)
from backend.database.user import get_user, create_user
from backend.database.strategy import create_strategy
from backend.database.backtest_history import create_backtest_history
from backend.routes.helpers import prepare_signal_with_condition
import sys
import os
import pandas as pd

# Add the backtest_utils directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import simplified interface functions
from backtest_utils.strategy_interface import (
    run_backtest_with_prepared_signals,
    search_and_get_pool_address,
    fetch_ohlc_data
)

router = APIRouter()

class ConditionModel(BaseModel):
    signal_id: int
    operator: str
    threshold: float

class StrategyModel(BaseModel):
    filterSignal_id: int
    buyCondition: ConditionModel
    sellCondition: ConditionModel
    positionSize: float
    maxPositionValue: float
    timeRange: Dict[str, str]
    wallet_address: str

class SignalInfo(BaseModel):
    signal_id: int
    signal_name: str
    signal_description: str

class StrategyWithSignals(BaseModel):
    filterSignal: SignalInfo
    buyCondition: ConditionModel
    sellCondition: ConditionModel
    positionSize: float
    maxPositionValue: float
    timeRange: Dict[str, str]
    
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

def filter_token_info(filter_signal_name: str, filter_signal_description: str):
    """Get token information based on filter signal"""
    msg = f"""Get the token name, token symbol, and token contract address for the token that meets the {filter_signal_name} condition: {filter_signal_description}. 
    No visualization. I just want the csv data of the contract address. 
    The csv data should have the following columns: token_name, token_symbol, token_contract_address (no need to mind the column order)
    """
    from agents.controller import process_with_claude
    conversation_history = [
        {
            "role": "user",
            "content": msg
        }
    ]
    response = process_with_claude(conversation_history)
    print("response", response)
    token_name = None
    token_symbol = None
    token_contract_address = None
    for item in response:
        if item["role"] == "tool" and item["name"] == "get_data":
            print("item", item)
            print("item['result']", item["content"]['file_path'])
            print("item['result']", item["content"]['df_head'])
            print("item['result']", item["content"]['description'])
            import pandas as pd
            df = pd.read_csv(item["content"]['file_path'])
            print(df.head())
            print(df.columns)
            if "token_name" in df.columns:
                token_name = df.iloc[0]['token_name']
            if "token_symbol" in df.columns:
                token_symbol = df.iloc[0]['token_symbol']
            if "token_contract_address" in df.columns:
                token_contract_address = df.iloc[0]['token_contract_address']
            # early stop the loop if all three variables are found
            if token_name and token_symbol and token_contract_address:
                break
    return token_name, token_symbol, token_contract_address



@router.post("/strategy/backtest")
async def run_backtest(strategy: StrategyModel, db: Session = Depends(get_db)):
    """Run backtest with the given strategy"""
    try:
        # Get or create user from wallet address
        user = get_user(db, strategy.wallet_address)
        if not user:
            user = create_user(db, strategy.wallet_address)
            print(f"Created new user for wallet: {strategy.wallet_address}")

        # Save strategy to database before running backtest
        saved_strategy = create_strategy(
            db=db,
            user_id=user.user_id,
            filter_signal_id=strategy.filterSignal_id,
            buy_condition_signal_id=strategy.buyCondition.signal_id,
            buy_condition_operator=strategy.buyCondition.operator,
            buy_condition_threshold=strategy.buyCondition.threshold,
            sell_condition_signal_id=strategy.sellCondition.signal_id,
            sell_condition_operator=strategy.sellCondition.operator,
            sell_condition_threshold=strategy.sellCondition.threshold,
            position_size=strategy.positionSize,
            max_position_value=strategy.maxPositionValue
        )
        
        print(f"Strategy saved to database with ID: {saved_strategy.strategy_id}")
        
        # Get signal information for each signal in the strategy
        filter_signal = get_signal_info(db, strategy.filterSignal_id)
        buy_signal = get_signal_info(db, strategy.buyCondition.signal_id)
        sell_signal = get_signal_info(db, strategy.sellCondition.signal_id)
        
        # Create complete strategy with signal information
        complete_strategy = StrategyWithSignals(
            filterSignal=filter_signal,
            buyCondition=ConditionModel(
                signal_id=strategy.buyCondition.signal_id,
                operator=strategy.buyCondition.operator,
                threshold=strategy.buyCondition.threshold
            ),
            sellCondition=ConditionModel(
                signal_id=strategy.sellCondition.signal_id,
                operator=strategy.sellCondition.operator,
                threshold=strategy.sellCondition.threshold
            ),
            positionSize=strategy.positionSize,
            maxPositionValue=strategy.maxPositionValue,
            timeRange=strategy.timeRange
        )
        
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
            pool_address = search_and_get_pool_address("eth", token_symbol)
            print(f"✅ Found pool address: {pool_address}")
            
            # Fetch OHLC data
            data_file_path = fetch_ohlc_data(
                network="eth",
                pool_address=pool_address,
                timeframe="1d",
                time_start=strategy.timeRange['start'],
                time_end=strategy.timeRange['end']
            )
            
            # Read the CSV file to get the DataFrame
            print(f"📖 Reading data from: {data_file_path}")
            df = pd.read_csv(data_file_path)
            
            print(f"📋 DataFrame columns: {list(df.columns)}")
            
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
            strategy.buyCondition.signal_id, 
            strategy.buyCondition.operator, 
            strategy.buyCondition.threshold, 
            'buy', 
            db
        )
        
        print("\n📉 Preparing sell signals...")
        df, sell_signal_column = prepare_signal_with_condition(
            df, 
            strategy.sellCondition.signal_id, 
            strategy.sellCondition.operator, 
            strategy.sellCondition.threshold, 
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
                    "buy_condition": f"{buy_signal.signal_name} {strategy.buyCondition.operator} {strategy.buyCondition.threshold}",
                    "sell_condition": f"{sell_signal.signal_name} {strategy.sellCondition.operator} {strategy.sellCondition.threshold}"
                }
            }
        
        # Set network and timeframe parameters
        network = "eth"  # You can make this configurable
        timeframe = "1d"  # You can make this configurable based on strategy
        
        # Step 3: Run backtest with the prepared signals (DECOUPLED APPROACH)
        print("\n" + "="*60) 
        print("🚀 RUNNING BACKTEST WITH DECOUPLED SIGNALS")
        print("="*60)
        
        backtest_result = run_backtest_with_prepared_signals(
            df=df,
            network=network,
            token_symbol=token_symbol,
            timeframe=timeframe,
            time_start=strategy.timeRange['start'],
            time_end=strategy.timeRange['end'],
            buy_signal_name=buy_signal.signal_name,
            sell_signal_name=sell_signal.signal_name
        )
        
    
        print("backtest_result")
        for key, result in backtest_result.items():
            print(key)
            print(result)
        
        # Save backtest history to database
        try:
            backtest_history = create_backtest_history(
                db=db,
                user_id=user.user_id,
                strategy_id=saved_strategy.strategy_id,
                time_start=strategy.timeRange['start'],
                time_end=strategy.timeRange['end'],
                trading_stats=backtest_result['trading_stats'],
                data_points=backtest_result.get('data_points'),
                network="eth",
                token_symbol=token_symbol,
                timeframe="1d"
            )
            print(f"✅ Saved backtest history with ID: {backtest_history.backtest_id}")
        except Exception as e:
            print(f"⚠️  Warning: Failed to save backtest history: {e}")
            # Don't fail the entire request if history saving fails
        
        # Return comprehensive result with decoupled signal information
        return {
            "status": "success",
            "strategy_id": saved_strategy.strategy_id,
            "strategy": complete_strategy,
            "fig": backtest_result.get('plotly_figure'),
            "backtest_results": {
                "trading_stats": backtest_result.get('trading_stats', {}),
                "data_points": backtest_result.get('data_points'),
                "time_range": backtest_result.get('time_range')
            },
            "signals": {
                "buy_signal": {
                    "name": buy_signal.signal_name,
                    "column": buy_signal_column,
                    "operator": strategy.buyCondition.operator,
                    "threshold": strategy.buyCondition.threshold,
                    "description": buy_signal.signal_description,
                    "info": backtest_result.get('buy_indicator_info')
                },
                "sell_signal": {
                    "name": sell_signal.signal_name,
                    "column": sell_signal_column,
                    "operator": strategy.sellCondition.operator,
                    "threshold": strategy.sellCondition.threshold,
                    "description": sell_signal.signal_description,
                    "info": backtest_result.get('sell_indicator_info')
                }
            },
            "token_info": {
                "name": token_name,
                "symbol": token_symbol,
                "contract_address": token_contract_address
            },
            "results": {
                "filterSignal": {
                    "id": filter_signal.signal_id,
                    "name": filter_signal.signal_name,
                    "description": filter_signal.signal_description
                },
                "buySignal": {
                    "id": buy_signal.signal_id,
                    "name": buy_signal.signal_name,
                    "description": buy_signal.signal_description
                },
                "sellSignal": {
                    "id": sell_signal.signal_id,
                    "name": sell_signal.signal_name,
                    "description": sell_signal.signal_description
                }
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error running backtest: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to run backtest: {str(e)}")

@router.post("/strategy/trade")
async def execute_trade(strategy: StrategyModel, db: Session = Depends(get_db)):
    """Execute trade with the given strategy"""
    try:
        # Get signal information for each signal in the strategy
        filter_signal = get_signal_info(db, strategy.filterSignal_id)
        buy_signal = get_signal_info(db, strategy.buyCondition.signal_id)
        sell_signal = get_signal_info(db, strategy.sellCondition.signal_id)
        
        # Create complete strategy with signal information
        complete_strategy = StrategyWithSignals(
            filterSignal=filter_signal,
            buyCondition=ConditionModel(
                signal_id=strategy.buyCondition.signal_id,
                operator=strategy.buyCondition.operator,
                threshold=strategy.buyCondition.threshold
            ),
            sellCondition=ConditionModel(
                signal_id=strategy.sellCondition.signal_id,
                operator=strategy.sellCondition.operator,
                threshold=strategy.sellCondition.threshold
            ),
            positionSize=strategy.positionSize,
            maxPositionValue=strategy.maxPositionValue,
            timeRange=strategy.timeRange
        )
        
        # TODO: Implement actual trade execution logic here
        # For now, return the complete strategy with signal information
        return {
            "status": "success",
            "strategy": complete_strategy,
            "trade_details": {
                "filterSignal": {
                    "id": filter_signal.signal_id,
                    "name": filter_signal.signal_name,
                    "description": filter_signal.signal_description
                },
                "buySignal": {
                    "id": buy_signal.signal_id,
                    "name": buy_signal.signal_name,
                    "description": buy_signal.signal_description
                },
                "sellSignal": {
                    "id": sell_signal.signal_id,
                    "name": sell_signal.signal_name,
                    "description": sell_signal.signal_description
                }
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error executing trade: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to execute trade") 

@router.get("/strategy/user/{wallet_address}")
async def get_user_strategies(wallet_address: str, db: Session = Depends(get_db)):
    """Get all strategies for a specific user"""
    try:
        # Get user from wallet address
        user = get_user(db, wallet_address)
        if not user:
            return {
                "status": "success",
                "strategies": []
            }
        
        # Get strategies for the user
        from backend.database.strategy import get_strategies_by_user
        strategies = get_strategies_by_user(db, user.user_id)
        
        # Format strategies with signal information
        formatted_strategies = []
        for strategy in strategies:
            try:
                # Get signal information for each condition
                filter_signal = get_signal_info(db, strategy.filter_signal_id)
                buy_signal = get_signal_info(db, strategy.buy_condition_signal_id)
                sell_signal = get_signal_info(db, strategy.sell_condition_signal_id)
                
                formatted_strategy = {
                    "strategy_id": strategy.strategy_id,
                    "created_at": strategy.created_at.isoformat(),
                    "position_size": strategy.position_size,
                    "max_position_value": strategy.max_position_value,
                    "filter_condition": {
                        "signal_id": filter_signal.signal_id,
                        "signal_name": filter_signal.signal_name,
                        "signal_description": filter_signal.signal_description
                    },
                    "buy_condition": {
                        "signal_id": buy_signal.signal_id,
                        "signal_name": buy_signal.signal_name,
                        "signal_description": buy_signal.signal_description,
                        "operator": strategy.buy_condition_operator,
                        "threshold": strategy.buy_condition_threshold
                    },
                    "sell_condition": {
                        "signal_id": sell_signal.signal_id,
                        "signal_name": sell_signal.signal_name,
                        "signal_description": sell_signal.signal_description,
                        "operator": strategy.sell_condition_operator,
                        "threshold": strategy.sell_condition_threshold
                    }
                }
                formatted_strategies.append(formatted_strategy)
                
            except Exception as e:
                print(f"Error formatting strategy {strategy.strategy_id}: {e}")
                continue
        
        print(f"Retrieved {len(formatted_strategies)} strategies for user {user.user_id}")
        
        return {
            "status": "success",
            "strategies": formatted_strategies
        }
        
    except Exception as e:
        print(f"Error fetching user strategies: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch strategies: {str(e)}")

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