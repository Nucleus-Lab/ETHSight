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
    signal_definition: str
    created_at: datetime
    
    class Config:
        orm_mode = True

# Define the Signal creation request model
class SignalCreate(BaseModel):
    canvas_id: int
    signal_definition: str

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
    # Verify canvas exists
    canvas = get_canvas(db, canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    signals = get_signals_for_canvas(db, canvas_id)
    return signals

# Get signal by ID
@router.get("/signals/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a signal by its ID"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal

# Create a new signal
@router.post("/signal", response_model=SignalResponse)
async def create_new_signal(signal: SignalCreate, db: Session = Depends(get_db)):
    """Create a new signal"""
    # Verify canvas exists
    canvas = get_canvas(db, signal.canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    # Create the signal
    new_signal = create_signal(db, signal.canvas_id, signal.signal_definition)
    return new_signal

# Get all signals for a specific user by wallet address
@router.get("/signals/user/{wallet_address}", response_model=List[SignalResponse])
async def get_user_signals(wallet_address: str, db: Session = Depends(get_db)):
    """Get all signals created by a specific user based on their wallet address"""
    # Verify user exists
    user = get_user(db, wallet_address)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    signals = get_signals_for_user_wallet(db, wallet_address)
    return signals 