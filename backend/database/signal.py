from typing import List, Optional
from datetime import datetime
from backend.database.models import SignalDB, CanvasDB, UserDB
from sqlalchemy.orm import Session

# Create a new signal
def create_signal(db, canvas_id: int, signal_name: str, signal_description: str) -> SignalDB:
    """Create a new signal in the database"""
    new_signal = SignalDB(
        canvas_id=canvas_id,
        signal_name=signal_name,
        signal_description=signal_description,
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
def update_signal(db, signal_id: int, signal_name: str, signal_description: str) -> Optional[SignalDB]:
    """Update an existing signal"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return None
    
    signal.signal_name = signal_name
    signal.signal_description = signal_description
    db.commit()
    db.refresh(signal)
    return signal

# Update signal code
def update_signal_code(db, signal_id: int, signal_code: str) -> Optional[SignalDB]:
    """Update the code for a specific signal"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return None
    
    signal.signal_code = signal_code
    db.commit()
    db.refresh(signal)
    print(f"Updated code for signal {signal_id}: {signal.signal_name}")
    return signal

# Get signal code by ID
def get_signal_code(db, signal_id: int) -> Optional[str]:
    """Get the code for a specific signal"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return None
    return signal.signal_code

# Check if signal has code
def signal_has_code(db, signal_id: int) -> bool:
    """Check if a signal has generated code stored"""
    signal = db.query(SignalDB).filter(SignalDB.signal_id == signal_id).first()
    if not signal:
        return False
    return signal.signal_code is not None and signal.signal_code.strip() != ""

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

def update_signal_calculation_code(db: Session, signal_id: int, signal_code: str, signal_column_name: str = None) -> SignalDB:
    """Update signal with calculation code and column name"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise Exception(f"Signal {signal_id} not found")
    
    signal.signal_code = signal_code
    # Store the signal column name in the description if not provided separately
    # You might want to add a separate column for this in the future
    
    db.commit()
    db.refresh(signal)
    
    print(f"Updated signal {signal_id} with calculation code")
    return signal

def get_signal_calculation_code(db: Session, signal_id: int) -> str:
    """Get signal calculation code from database"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        raise Exception(f"Signal {signal_id} not found")
    
    return signal.signal_code

def signal_has_calculation_code(db: Session, signal_id: int) -> bool:
    """Check if signal has calculation code stored"""
    signal = get_signal_by_id(db, signal_id)
    if not signal:
        return False
    
    return signal.signal_code is not None and signal.signal_code.strip() != "" 