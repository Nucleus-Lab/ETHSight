from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database.models import StrategyDB
from typing import List, Optional

def create_strategy(
    db: Session,
    user_id: int,
    filter_signal_id: int,
    buy_condition_signal_id: int,
    buy_condition_operator: str,
    buy_condition_threshold: float,
    sell_condition_signal_id: int,
    sell_condition_operator: str,
    sell_condition_threshold: float,
    position_size: float,
    max_position_value: float
) -> StrategyDB:
    """Create a new strategy in the database"""
    
    strategy = StrategyDB(
        user_id=user_id,
        filter_signal_id=filter_signal_id,
        buy_condition_signal_id=buy_condition_signal_id,
        buy_condition_operator=buy_condition_operator,
        buy_condition_threshold=str(buy_condition_threshold),
        sell_condition_signal_id=sell_condition_signal_id,
        sell_condition_operator=sell_condition_operator,
        sell_condition_threshold=str(sell_condition_threshold),
        position_size=str(position_size),
        max_position_value=str(max_position_value)
    )
    
    print(f"Creating strategy in database for user_id: {user_id}")
    
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    print(f"Strategy created with ID: {strategy.strategy_id}")
    return strategy

def get_strategy_by_id(db: Session, strategy_id: int) -> Optional[StrategyDB]:
    """Get a strategy by its ID"""
    return db.query(StrategyDB).filter(StrategyDB.strategy_id == strategy_id).first()

def get_strategies_by_user(db: Session, user_id: int, limit: int = 100) -> List[StrategyDB]:
    """Get all strategies for a specific user"""
    return db.query(StrategyDB).filter(
        StrategyDB.user_id == user_id
    ).order_by(desc(StrategyDB.created_at)).limit(limit).all()

def update_strategy(
    db: Session,
    strategy_id: int,
    **kwargs
) -> Optional[StrategyDB]:
    """Update a strategy"""
    strategy = get_strategy_by_id(db, strategy_id)
    if not strategy:
        return None
    
    # Convert numeric fields to strings for storage
    if 'buy_condition_threshold' in kwargs:
        kwargs['buy_condition_threshold'] = str(kwargs['buy_condition_threshold'])
    if 'sell_condition_threshold' in kwargs:
        kwargs['sell_condition_threshold'] = str(kwargs['sell_condition_threshold'])
    if 'position_size' in kwargs:
        kwargs['position_size'] = str(kwargs['position_size'])
    if 'max_position_value' in kwargs:
        kwargs['max_position_value'] = str(kwargs['max_position_value'])
    
    for key, value in kwargs.items():
        if hasattr(strategy, key):
            setattr(strategy, key, value)
    
    db.commit()
    db.refresh(strategy)
    return strategy

def delete_strategy(db: Session, strategy_id: int) -> bool:
    """Delete a strategy"""
    strategy = get_strategy_by_id(db, strategy_id)
    if not strategy:
        return False
    
    db.delete(strategy)
    db.commit()
    return True 