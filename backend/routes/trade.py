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
import asyncio

router = APIRouter()

# Global dictionary to track active monitors
active_monitors = {}
# Global dictionary to track all monitors (even if SSE closed) for cleanup
all_monitors = {}
# Add a lock for thread-safe access to the global dictionaries
monitor_lock = asyncio.Lock()
# Track request processing to prevent race conditions
processing_requests = {}
processing_lock = asyncio.Lock()

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
        print(f"🔄 [EXECUTE TRADE] Starting trade execution for strategy {strategy_id}")
        
        # Thread-safe check for existing monitor
        async with monitor_lock:
            print(f"🔍 [EXECUTE TRADE] Before cleanup - Active monitors: {list(active_monitors.keys())}, All monitors: {list(all_monitors.keys())}")
            
            # Force cleanup of ANY existing monitors for this strategy
            existing_monitors = []
            
            if strategy_id in active_monitors:
                existing_monitor = active_monitors[strategy_id]
                existing_monitors.append(("active", existing_monitor))
                print(f"⚠️ [EXECUTE TRADE] Strategy {strategy_id} already has an active monitor (ID: {id(existing_monitor)}, is_monitoring: {existing_monitor.is_monitoring}). Force stopping.")
            
            if strategy_id in all_monitors:
                existing_monitor = all_monitors[strategy_id]
                # Only add if it's a different instance
                if not any(monitor is existing_monitor for _, monitor in existing_monitors):
                    existing_monitors.append(("all", existing_monitor))
                    print(f"⚠️ [EXECUTE TRADE] Strategy {strategy_id} found in all_monitors (ID: {id(existing_monitor)}, is_monitoring: {existing_monitor.is_monitoring}). Force stopping.")
            
            # Force stop ALL existing monitors
            for source, monitor in existing_monitors:
                monitor_id = id(monitor)
                print(f"🛑 [EXECUTE TRADE] Force stopping {source} monitor {monitor_id}")
                monitor.is_monitoring = False  # Force set to False immediately
                monitor.stop()
                print(f"✅ [EXECUTE TRADE] Stopped {source} monitor {monitor_id}")
            
            # Clean up dictionaries
            if strategy_id in active_monitors:
                del active_monitors[strategy_id]
                print(f"🗑️ [EXECUTE TRADE] Removed {strategy_id} from active_monitors")
            if strategy_id in all_monitors:
                del all_monitors[strategy_id]
                print(f"🗑️ [EXECUTE TRADE] Removed {strategy_id} from all_monitors")
            
            # Wait a moment for cleanup to complete
            if existing_monitors:
                await asyncio.sleep(0.2)
                print(f"⏱️ [EXECUTE TRADE] Waited for cleanup of {len(existing_monitors)} monitors")
            
            print(f"🔍 [EXECUTE TRADE] After cleanup - Active monitors: {list(active_monitors.keys())}, All monitors: {list(all_monitors.keys())}")
        
        # Get strategy from database
        strategy = get_strategy_by_id(db, strategy_id)
        if not strategy:
            print(f"❌ [EXECUTE TRADE] Strategy {strategy_id} not found")
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
        
        # Create and track the monitor with thread safety
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
        
        # Thread-safe addition to dictionaries
        async with monitor_lock:
            active_monitors[strategy_id] = monitor
            all_monitors[strategy_id] = monitor
            print(f"✅ [EXECUTE TRADE] Added strategy {strategy_id} to active_monitors. Monitor ID: {id(monitor)}, Current active: {list(active_monitors.keys())}")
            print(f"🔍 [EXECUTE TRADE] Final state - Active monitors: {list(active_monitors.keys())}, All monitors: {list(all_monitors.keys())}")

        async def event_generator():
            """Generate SSE events for trade updates"""
            monitor_id = id(monitor)
            print(f"🎬 [SSE GENERATOR] Starting for strategy {strategy_id}, monitor ID: {monitor_id}")
            try:
                async for update in monitor.monitor_and_trade():
                    # Check if monitor has been stopped before yielding each update
                    if not monitor.is_monitoring:
                        print(f"🛑 SSE generator: Monitor stopped for strategy {strategy_id} (ID: {monitor_id}), breaking SSE loop")
                        break
                        
                    print(f"📤 Backend yielding update for strategy {strategy_id} (monitor ID: {monitor_id})")
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
                    if not monitor.is_monitoring:
                        print(f"🛑 SSE generator: Monitor stopped for strategy {strategy_id} (ID: {monitor_id}) after yield, breaking SSE loop")
                        break
                        
            except Exception as e:
                print(f"❌ Error in event generator for strategy {strategy_id} (monitor ID: {monitor_id}): {str(e)}")
                print(traceback.format_exc())
                yield {
                    "event": "error", 
                    "data": json.dumps({"error": str(e)})
                }
            finally:
                print(f"🏁 [SSE GENERATOR] Finally block for strategy {strategy_id}, monitor ID: {monitor_id}")
                # Clean up monitor when SSE connection ends with thread safety
                async with monitor_lock:
                    if strategy_id in active_monitors:
                        # Stop the monitor before removing it
                        monitor_to_stop = active_monitors[strategy_id]
                        current_monitor_id = id(monitor_to_stop)
                        print(f"🛑 SSE cleanup: Found monitor in active_monitors (ID: {current_monitor_id}) for strategy {strategy_id}")
                        monitor_to_stop.stop()
                        print(f"🛑 SSE cleanup: Stopped monitor for strategy {strategy_id} (ID: {current_monitor_id})")
                        
                        del active_monitors[strategy_id]
                        print(f"🧹 SSE cleanup: Removed monitor for strategy {strategy_id} from active_monitors. Remaining active: {list(active_monitors.keys())}")
                        
                        # Keep in all_monitors for potential manual stop
                        print(f"ℹ️ Monitor for strategy {strategy_id} (ID: {current_monitor_id}) kept in all_monitors for manual stop")
                    else:
                        print(f"🧹 SSE cleanup: Strategy {strategy_id} already removed from active monitors")
        
        return EventSourceResponse(event_generator())
            
    except HTTPException as e:
        print(f"HTTP Exception: {str(e)}")
        raise e
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/trade/{strategy_id}/stop")
async def stop_trade(strategy_id: int, db: Session = Depends(get_db)):
    """Stop live trading for the given strategy"""
    try:
        print(f"🛑 [STOP TRADE] Stopping trade execution for strategy {strategy_id}")
        
        # Get strategy from database to verify it exists
        strategy = get_strategy_by_id(db, strategy_id)
        if not strategy:
            print(f"❌ [STOP TRADE] Strategy {strategy_id} not found")
            raise HTTPException(status_code=404, detail=f"Strategy with ID {strategy_id} not found")
        
        # Thread-safe access to monitor dictionaries
        async with monitor_lock:
            # Debug: Show current active monitors
            print(f"🔍 [STOP TRADE] Stop request for strategy {strategy_id}. Current active monitors: {list(active_monitors.keys())}")
            print(f"🔍 [STOP TRADE] All monitors (including SSE-closed): {list(all_monitors.keys())}")
            
            # Show detailed info about monitors
            if strategy_id in active_monitors:
                active_monitor = active_monitors[strategy_id]
                print(f"🔍 [STOP TRADE] Active monitor found - ID: {id(active_monitor)}, is_monitoring: {active_monitor.is_monitoring}")
            
            if strategy_id in all_monitors:
                all_monitor = all_monitors[strategy_id]
                print(f"🔍 [STOP TRADE] All_monitors entry found - ID: {id(all_monitor)}, is_monitoring: {all_monitor.is_monitoring}")
            
            # Try to stop ALL monitors for this strategy (both active and all)
            monitors_stopped = []
            
            # Stop active monitor
            if strategy_id in active_monitors:
                monitor = active_monitors[strategy_id]
                monitor_id = id(monitor)
                print(f"🛑 [STOP TRADE] Stopping active monitor {monitor_id} for strategy {strategy_id}")
                monitor.stop()
                monitors_stopped.append(f"active:{monitor_id}")
                del active_monitors[strategy_id]
                print(f"🗑️ [STOP TRADE] Removed strategy {strategy_id} from active_monitors")
            
            # Stop all_monitors entry (might be different instance)
            if strategy_id in all_monitors:
                monitor = all_monitors[strategy_id]
                monitor_id = id(monitor)
                # Only stop if it's a different instance than the active one
                if f"active:{monitor_id}" not in monitors_stopped:
                    print(f"🛑 [STOP TRADE] Stopping all_monitors monitor {monitor_id} for strategy {strategy_id}")
                    monitor.stop()
                    monitors_stopped.append(f"all:{monitor_id}")
                else:
                    print(f"🔍 [STOP TRADE] All_monitors monitor {monitor_id} is same as active monitor, already stopped")
                del all_monitors[strategy_id]
                print(f"🗑️ [STOP TRADE] Removed strategy {strategy_id} from all_monitors")
            
            if monitors_stopped:
                print(f"✅ [STOP TRADE] Successfully stopped monitors for strategy {strategy_id}: {monitors_stopped}")
                return {
                    "success": True,
                    "message": f"Trading stopped for strategy {strategy_id}. Stopped monitors: {monitors_stopped}",
                    "strategy_id": strategy_id
                }
            else:
                print(f"❌ [STOP TRADE] No monitor found for strategy {strategy_id} in either active or all monitors")
                return {
                    "success": False,
                    "message": f"No trading session found for strategy {strategy_id}",
                    "strategy_id": strategy_id
                }
            
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ [STOP TRADE] Error stopping trade: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy/trade/{strategy_id}/force-stop")
async def force_stop_trade(strategy_id: int):
    """Force stop all trading instances for a strategy - emergency cleanup"""
    try:
        print(f"🚨 [FORCE STOP] Emergency stop for strategy {strategy_id}")
        
        monitors_found = []
        monitors_stopped = []
        
        async with monitor_lock:
            # Force stop and remove from active_monitors
            if strategy_id in active_monitors:
                monitor = active_monitors[strategy_id]
                monitor_id = id(monitor)
                print(f"🛑 [FORCE STOP] Stopping active monitor {monitor_id}")
                monitor.is_monitoring = False  # Force set to False
                monitor.stop()
                monitors_found.append(f"active:{monitor_id}")
                monitors_stopped.append(f"active:{monitor_id}")
                del active_monitors[strategy_id]
                print(f"🗑️ [FORCE STOP] Removed from active_monitors")
            
            # Force stop and remove from all_monitors
            if strategy_id in all_monitors:
                monitor = all_monitors[strategy_id]
                monitor_id = id(monitor)
                if f"active:{monitor_id}" not in monitors_found:
                    print(f"🛑 [FORCE STOP] Stopping all_monitors monitor {monitor_id}")
                    monitor.is_monitoring = False  # Force set to False
                    monitor.stop()
                    monitors_found.append(f"all:{monitor_id}")
                    monitors_stopped.append(f"all:{monitor_id}")
                del all_monitors[strategy_id]
                print(f"🗑️ [FORCE STOP] Removed from all_monitors")
        
        print(f"🚨 [FORCE STOP] Completed. Found: {monitors_found}, Stopped: {monitors_stopped}")
        
        return {
            "success": True,
            "message": f"Force stopped all monitors for strategy {strategy_id}",
            "monitors_found": monitors_found,
            "monitors_stopped": monitors_stopped,
            "strategy_id": strategy_id
        }
        
    except Exception as e:
        print(f"❌ [FORCE STOP] Error: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "message": f"Error during force stop: {str(e)}",
            "strategy_id": strategy_id
        }

@router.get("/debug/monitors")
async def debug_monitors():
    """Debug endpoint to show all current monitor instances"""
    async with monitor_lock:
        monitor_info = {
            "active_monitors": {},
            "all_monitors": {},
            "summary": {
                "active_count": len(active_monitors),
                "all_count": len(all_monitors),
                "active_keys": list(active_monitors.keys()),
                "all_keys": list(all_monitors.keys())
            }
        }
        
        # Get detailed info about active monitors
        for strategy_id, monitor in active_monitors.items():
            monitor_info["active_monitors"][strategy_id] = {
                "monitor_id": id(monitor),
                "is_monitoring": getattr(monitor, 'is_monitoring', 'N/A'),
                "strategy_id": getattr(monitor, 'strategy_id', 'N/A')
            }
        
        # Get detailed info about all monitors
        for strategy_id, monitor in all_monitors.items():
            monitor_info["all_monitors"][strategy_id] = {
                "monitor_id": id(monitor),
                "is_monitoring": getattr(monitor, 'is_monitoring', 'N/A'),
                "strategy_id": getattr(monitor, 'strategy_id', 'N/A')
            }
        
        print(f"🔍 [DEBUG] Current monitor state: {monitor_info}")
        return monitor_info