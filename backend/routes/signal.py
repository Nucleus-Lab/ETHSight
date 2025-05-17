from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.signal import get_signals_for_canvas, get_all_signals, create_signal, get_signal_by_id, get_signals_for_user_wallet
from backend.database.canvas import get_canvas
from backend.database.user import get_user

from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Define the Signal response model for API
class SignalResponse(BaseModel):
    signal_id: int
    canvas_id: int
    signal_name: str
    signal_description: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# Define the Signal creation request model
class SignalCreate(BaseModel):
    canvas_id: int
    wallet_address: str
    signal_name: str
    signal_description: str
    temp_signal_id: Optional[str] = None  # For reference only, not stored in DB

# Get all signals
@router.get("/signals", response_model=List[SignalResponse])
async def get_signals(db: Session = Depends(get_db)):
    """Get all signals"""
    signals = get_all_signals(db)
    return signals

# Get signals for a specific canvas
@router.get("/canvas/{canvas_id}/signals", response_model=List[SignalResponse])
async def get_canvas_signals(canvas_id: int, db: Session = Depends(get_db)):
    """Get all signals for a specific canvas"""
    try:
        signals = get_signals_for_canvas(db, canvas_id)
        
        return [{
            "signal_id": signal.signal_id,
            "canvas_id": signal.canvas_id,
            "signal_name": signal.signal_name,
            "signal_description": signal.signal_description,
            "created_at": signal.created_at
        } for signal in signals]
    except Exception as e:
        print(f"Error getting canvas signals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get signals")

# Get signal by ID
@router.get("/signal/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a signal by its ID"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal with id {signal_id} not found")
    
    return {
        "signal_id": signal.signal_id,
        "canvas_id": signal.canvas_id,
        "signal_name": signal.signal_name,
        "signal_description": signal.signal_description,
        "created_at": signal.created_at
    }

# Create a new signal
@router.post("/signal", response_model=SignalResponse)
async def create_new_signal(signal: SignalCreate, db: Session = Depends(get_db)):
    """Create a new signal in the database"""
    try:
        # Create signal with the name and description
        new_signal = create_signal(
            db, 
            canvas_id=signal.canvas_id, 
            signal_name=signal.signal_name, 
            signal_description=signal.signal_description
        )
        
        return {
            "signal_id": new_signal.signal_id,
            "canvas_id": new_signal.canvas_id,
            "signal_name": new_signal.signal_name,
            "signal_description": new_signal.signal_description,
            "created_at": new_signal.created_at
        }
    except Exception as e:
        print(f"Error creating signal: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create signal")

# Get all signals for a specific user by wallet address
@router.get("/signals/user/{wallet_address}", response_model=List[SignalResponse])
async def get_user_signals(wallet_address: str, db: Session = Depends(get_db)):
    """Get all signals for a specific user by wallet address"""
    try:
        signals = get_signals_for_user_wallet(db, wallet_address)
        
        return [{
            "signal_id": signal.signal_id,
            "canvas_id": signal.canvas_id,
            "signal_name": signal.signal_name,
            "signal_description": signal.signal_description,
            "created_at": signal.created_at
        } for signal in signals]
    except Exception as e:
        print(f"Error getting user signals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get signals") 