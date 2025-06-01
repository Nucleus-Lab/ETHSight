from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import get_signal_by_id
import sys
import os

# Add the backtest_utils directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import simplified interface functions
from backtest_utils.strategy_interface import (
    generate_indicator_from_prompt,
    run_backtest_with_indicators
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
        
        # # Generate AI indicators
        # print("\nGenerating buy indicator...")
        # buy_indicator_name = buy_signal.signal_name.replace(" ", "_")
        # buy_indicator_path, buy_indicator_name = generate_indicator_from_prompt(
        #     user_prompt=buy_signal.signal_description,
        #     indicator_name=buy_indicator_name
        # )
        # print("buy_indicator_path", buy_indicator_path)
        # print("buy_indicator_name", buy_indicator_name)
        
        # print("\nGenerating sell indicator...")
        # sell_indicator_name = sell_signal.signal_name.replace(" ", "_")
        # sell_indicator_path, sell_indicator_name = generate_indicator_from_prompt(
        #     user_prompt=sell_signal.signal_description,
        #     indicator_name=sell_indicator_name
        # )
        # print("sell_indicator_path", sell_indicator_path)
        # print("sell_indicator_name", sell_indicator_name)
        
        # Set network and timeframe parameters
        buy_indicator_name = "macd_line"
        buy_indicator_path = "indicators/macd_line.py"
        sell_indicator_name = "trading_volume"
        sell_indicator_path = "indicators/trading_volume.py"
        network = "eth"  # You can make this configurable
        timeframe = "1d"  # You can make this configurable based on strategy
        
        # Run backtest with the generated indicators
        print("\nRunning backtest...")
        backtest_result = run_backtest_with_indicators(
            network=network,
            token_symbol=token_symbol,
            timeframe=timeframe,
            time_start=strategy.timeRange['start'],
            time_end=strategy.timeRange['end'],
            buy_indicator_name=buy_indicator_name,
            sell_indicator_name=sell_indicator_name
        )
        
    
        print("backtest_result")
        for key, result in backtest_result.items():
            print(key)
            print(result)
        
        # Return comprehensive result
        return {
            "status": "success",
            "strategy": complete_strategy,
            "fig": backtest_result['plotly_figure'],
            "backtest_results": {
                "trading_stats": backtest_result['trading_stats'],
                "plotly_figure": backtest_result['plotly_figure'],
                "data_points": backtest_result['data_points'],
                "time_range": backtest_result['time_range']
            },
            "indicators": {
                "buy_indicator": {
                    "name": buy_indicator_name,
                    "path": buy_indicator_path,
                    "info": backtest_result.get('buy_indicator_info')
                },
                "sell_indicator": {
                    "name": sell_indicator_name,
                    "path": sell_indicator_path,
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