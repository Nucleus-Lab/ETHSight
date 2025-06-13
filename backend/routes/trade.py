from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from sqlalchemy.orm import Session
import traceback
from backend.database import get_db
from backend.database.signal import get_signal_by_id
from backend.database.strategy import get_strategy_by_id
from backend.routes.helpers import CAKE, TradeMonitor
import json
from sse_starlette.sse import EventSourceResponse
import pandas as pd
from datetime import datetime

router = APIRouter()

# Global dictionary to track active monitors
active_monitors = {}
# Global dictionary to track all monitors (even if SSE closed) for cleanup
all_monitors = {}

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

def safe_json_serialize(obj):
    """Convert pandas/datetime objects to JSON-serializable formats"""
    if isinstance(obj, dict):
        return {key: safe_json_serialize(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):  # Any datetime-like object
        return obj.isoformat()
    else:
        return obj

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
        
        # Create and track the monitor
        monitor = TradeMonitor(
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
        )
        
        # Add to active monitors and all monitors
        active_monitors[strategy_id] = monitor
        all_monitors[strategy_id] = monitor
        print(f"✅ Added strategy {strategy_id} to active_monitors. Monitor ID: {id(monitor)}, Current active: {list(active_monitors.keys())}", flush=True)

        async def event_generator():
            """Generate SSE events for trade updates"""
            try:
                async for update in monitor.monitor_and_trade():
                    # Check if monitor has been stopped before yielding each update
                    if not monitor.is_monitoring or monitor._force_stop:
                        print(f"🛑 SSE generator: Monitor stopped for strategy {strategy_id}, breaking SSE loop", flush=True)
                        break
                        
                    print("Backend yielding update")
                    if update['status'] == 'error':
                        # For EventSourceResponse, yield dict format
                        yield {
                            "event": "error",
                            "data": json.dumps({"error": update['error']})
                        }
                    else:
                        # Convert Plotly figure to JSON
                        if 'fig' in update:
                            update['fig'] = update['fig'].to_json()
                        
                        # Safely serialize any pandas timestamps or datetime objects
                        update = safe_json_serialize(update)
                        
                        # For EventSourceResponse, yield dict format (no event type = default message)
                        yield {
                            "data": json.dumps(update)
                        }
                        
                    # Additional stop check after yielding
                    if not monitor.is_monitoring or monitor._force_stop:
                        print(f"🛑 SSE generator: Monitor stopped for strategy {strategy_id} after yield, breaking SSE loop", flush=True)
                        break
                        
            except Exception as e:
                print(f"❌ Error in event generator for strategy {strategy_id}: {str(e)}", flush=True)
                print(traceback.format_exc())
                yield {
                    "event": "error", 
                    "data": json.dumps({"error": str(e)})
                }
            finally:
                # Clean up monitor when SSE connection ends
                if strategy_id in active_monitors:
                    # Stop the monitor before removing it
                    monitor_to_stop = active_monitors[strategy_id]
                    monitor_to_stop.stop()
                    print(f"🛑 SSE cleanup: Stopped monitor for strategy {strategy_id}", flush=True)
                    
                    del active_monitors[strategy_id]
                    print(f"🧹 SSE cleanup: Removed monitor for strategy {strategy_id} from active_monitors. Remaining active: {list(active_monitors.keys())}", flush=True)
                    
                    # Keep in all_monitors for potential manual stop
                    print(f"ℹ️ Monitor for strategy {strategy_id} kept in all_monitors for manual stop", flush=True)
                else:
                    print(f"🧹 SSE cleanup: Strategy {strategy_id} already removed from active monitors", flush=True)
        
        return EventSourceResponse(event_generator())
            
    except HTTPException as e:
        print(f"HTTP Exception: {str(e)}")  # Add logging
        raise e
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Add logging
        print(traceback.format_exc())  # Add stack trace
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/trade/{strategy_id}/stop")
async def stop_trade(strategy_id: int, db: Session = Depends(get_db)):
    """Stop live trading for the given strategy"""
    try:
        print(f"Stopping trade execution for strategy {strategy_id}")
        
        # Get strategy from database to verify it exists
        strategy = get_strategy_by_id(db, strategy_id)
        if not strategy:
            print(f"Strategy {strategy_id} not found")
            raise HTTPException(status_code=404, detail=f"Strategy with ID {strategy_id} not found")
        
        # Debug: Show current active monitors
        print(f"🔍 Stop request for strategy {strategy_id}. Current active monitors: {list(active_monitors.keys())}", flush=True)
        print(f"🔍 All monitors (including SSE-closed): {list(all_monitors.keys())}", flush=True)
        
        # Try to stop the monitor - check both active and all monitors
        monitor = None
        if strategy_id in active_monitors:
            monitor = active_monitors[strategy_id]
            del active_monitors[strategy_id]
            print(f"🗑️ Removed strategy {strategy_id} from active monitors", flush=True)
        elif strategy_id in all_monitors:
            monitor = all_monitors[strategy_id]
            print(f"⚠️ Found strategy {strategy_id} in all_monitors but not active (SSE likely closed)", flush=True)
        
        if monitor:
            print(f"🔍 Found monitor for strategy {strategy_id}. Monitor ID: {id(monitor)}", flush=True)
            # Check if monitor is still running
            if hasattr(monitor, 'is_monitoring') and monitor.is_monitoring:
                print(f"🛑 Calling stop() on monitor {id(monitor)} for strategy {strategy_id}", flush=True)
                monitor.stop()
                print(f"✅ Successfully stopped trade monitor for strategy {strategy_id}", flush=True)
            else:
                print(f"⚠️ Monitor for strategy {strategy_id} was already stopped (is_monitoring: {getattr(monitor, 'is_monitoring', 'N/A')})", flush=True)
            
            # Clean up from all_monitors
            if strategy_id in all_monitors:
                del all_monitors[strategy_id]
                print(f"🗑️ Removed strategy {strategy_id} from all_monitors", flush=True)
            
            return {
                "success": True,
                "message": f"Trading stopped for strategy {strategy_id}",
                "strategy_id": strategy_id
            }
        else:
            print(f"❌ No monitor found for strategy {strategy_id} in either active or all monitors", flush=True)
            return {
                "success": False,
                "message": f"No trading session found for strategy {strategy_id}",
                "strategy_id": strategy_id
            }
            
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error stopping trade: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))