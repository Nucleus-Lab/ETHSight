from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import get_signal_by_id

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
        
        # TODO: Implement actual backtest logic here
        # get the signal name and description for the filterSignal
        filter_signal_name = filter_signal.signal_name
        filter_signal_description = filter_signal.signal_description
        # get the token name, token symbol, and token contract address for the token that meets the filterSignal condition
        # token_name, token_symbol, token_contract_address = filter_token_info(filter_signal_name, filter_signal_description)
        
        token_name = "ETH"
        token_symbol = "ETH"
        token_contract_address = "0x0000000000000000000000000000000000000000"
        
        print("token_name", token_name)
        print("token_symbol", token_symbol)
        print("token_contract_address", token_contract_address)
        
        # prepare the arguments for the get_ohlcv function
        print("timerange start", strategy.timeRange['start'])
        print("timerange end", strategy.timeRange['end'])
        
        
        ARGS = {
            "time_start": strategy.timeRange['start'],
            "time_end": strategy.timeRange['end'],
            "time_period": "daily",
            "count": 10,
            "interval": "daily",
            "convert": "USD"
        }

        # get the ohlcv data for the token
        import os
        from agents.controller import CMCAPI
        import uuid
        api_key = os.getenv("CMC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="CMC_API_KEY not found in environment variables")
        cmc = CMCAPI(api_key=api_key)
        df = cmc.get_ohlcv(
            symbol=token_symbol,
            time_period=ARGS.get("time_period", "daily"),
            time_start=ARGS["time_start"],
            time_end=ARGS["time_end"],
            count=ARGS.get("count", 10),
            interval=ARGS.get("interval", "daily"),
            convert=ARGS.get("convert", "USD")
        )
        if df is not None and not df.empty:
            # Generate a unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_id = str(uuid.uuid4())
            file_path = f"data/cmc_data/cmc_{token_symbol}_{ARGS.get('interval', '1d')}_{timestamp}_{file_id}.csv"
            
            # Save to CSV
            df.to_csv(file_path)
            
        print("columns", df.columns)
            
        print("file_path", file_path)
        
        # prepare the df for backtest
        
        
        # backtest function
        
        
        # For now, return the complete strategy with signal information
        return {
            "status": "success",
            "strategy": complete_strategy,
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
        raise HTTPException(status_code=500, detail="Failed to run backtest")

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