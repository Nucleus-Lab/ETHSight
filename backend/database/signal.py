from typing import List, Optional
from datetime import datetime
from backend.database.models import SignalDB, CanvasDB, UserDB

# Create a new signal
def create_signal(db, canvas_id: int, signal_definition: str) -> SignalDB:
    """Create a new signal in the database"""
    new_signal = SignalDB(
        canvas_id=canvas_id,
        signal_definition=signal_definition,
        created_at=datetime.utcnow()
    )
    db.add(new_signal)
    db.commit()
    db.refresh(new_signal)
    return new_signal

# Get signal by ID
def get_signal_by_id(db, signal_id: int) -> Optional[SignalDB]:
    """Get a signal by its ID"""
    return db.query(SignalDB)\
        .filter(SignalDB.signal_id == signal_id)\
        .first()

# Get all signals for a canvas
def get_signals_for_canvas(db, canvas_id: int) -> List[SignalDB]:
    """Get all signals for a specific canvas"""
    return db.query(SignalDB)\
        .filter(SignalDB.canvas_id == canvas_id)\
        .order_by(SignalDB.created_at.desc())\
        .all()

# Get all signals
def get_all_signals(db) -> List[SignalDB]:
    """Get all signals"""
    return db.query(SignalDB)\
        .order_by(SignalDB.created_at.desc())\
        .all()

# Update a signal
def update_signal(db, signal_id: int, signal_definition: str) -> Optional[SignalDB]:
    """Update an existing signal"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return None
    
    signal.signal_definition = signal_definition
    db.commit()
    db.refresh(signal)
    return signal

# Delete a signal
def delete_signal(db, signal_id: int) -> bool:
    """Delete a signal by its ID"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return False
    
    db.delete(signal)
    db.commit()
    return True

# Get all signals for a user by wallet address
def get_signals_for_user_wallet(db, wallet_address: str) -> List[SignalDB]:
    """Get all signals created by a specific user based on their wallet address"""
    return db.query(SignalDB)\
        .join(CanvasDB, SignalDB.canvas_id == CanvasDB.canvas_id)\
        .join(UserDB, CanvasDB.user_id == UserDB.user_id)\
        .filter(UserDB.wallet_address == wallet_address)\
        .order_by(SignalDB.created_at.desc())\
        .all() 