from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import get_signal_by_id
from backend.database.strategy import get_strategy_by_id
from backend.routes.helpers import CAKE, start_trade_monitor
import json
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

class TradeRequest(BaseModel):
    strategy_id: int
    # TODO: add more parameters later

class TradeResponse(BaseModel):
    event: str
    data: Dict[str, Any]

class SignalInfo(BaseModel):
    signal_id: int
    signal_name: str
    signal_description: str

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

@router.get("/strategy/trade/{strategy_id}")
async def execute_trade(strategy_id: int, db: Session = Depends(get_db)):
    """Execute trade with the given strategy"""
    try:
        print(f"Starting trade execution for strategy {strategy_id}")  # Add logging
        
        # Get strategy from database
        strategy = get_strategy_by_id(db, strategy_id)
        if not strategy:
            print(f"Strategy {strategy_id} not found")  # Add logging
            raise HTTPException(status_code=404, detail=f"Strategy with ID {strategy_id} not found")
            
        # For now, use hardcoded values - you can uncomment the line below to use the AI agent
        # token_name, token_symbol, token_contract_address = filter_token_info(filter_signal_name, filter_signal_description)
        token_name = "PancakeSwap Token"
        token_symbol = "CAKE"
        token_contract_address = CAKE  # Using the constant from helpers.py
        
        print(f"\n🔄 Starting trade monitor for {token_symbol}")
        print(f"💰 Position size: {strategy.position_size} BNB")
        
        # TODO:
        # For testing on BSC Testnet, we'll use CAKE pool
        # In production, this should be determined by the token_contract_address
        pool_address = "0x0ed7e52944161450477ee417de9cd3a859b14fd0"  # CAKE-BNB pool on BSC
        network = "bsc"
        
        async def event_generator():
            """Generate SSE events for trade updates"""
            try:
                async for update in start_trade_monitor(
                    db=db,
                    strategy_id=strategy_id,
                    network=network,
                    pool_address=pool_address,
                    buy_signal_id=strategy.buy_condition_signal_id,
                    buy_operator=strategy.buy_condition_operator,
                    buy_threshold=float(strategy.buy_condition_threshold),
                    sell_signal_id=strategy.sell_condition_signal_id,
                    sell_operator=strategy.sell_condition_operator,
                    sell_threshold=float(strategy.sell_condition_threshold),
                    position_size=float(strategy.position_size)
                ):
                    print("update", update)
                    if update['status'] == 'error':
                        yield {
                            "event": "error",
                            "data": json.dumps({"error": update['error']})
                        }
                    else:
                        # Convert Plotly figure to JSON
                        if 'fig' in update:
                            update['fig'] = update['fig'].to_json()
                            
                        yield {
                            "event": "update",
                            "data": json.dumps(update)
                        }
                        
            except Exception as e:
                print(f"Error in event generator: {str(e)}")
                print(traceback.format_exc())
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
        
        return EventSourceResponse(event_generator())
            
    except HTTPException as e:
        print(f"HTTP Exception: {str(e)}")  # Add logging
        raise e
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Add logging
        print(traceback.format_exc())  # Add stack trace
        raise HTTPException(status_code=500, detail=str(e))