from sqlalchemy.orm import Session
from backend.database.models import BacktestHistoryDB
from datetime import datetime
from typing import List, Optional

def create_backtest_history(
    db: Session,
    user_id: int,
    strategy_id: int,
    time_start: str,
    time_end: str,
    trading_stats: dict,
    data_points: int = None,
    network: str = None,
    token_symbol: str = None,
    timeframe: str = None
) -> BacktestHistoryDB:
    """
    Create a new backtest history record
    
    Args:
        db: Database session
        user_id: User ID
        strategy_id: Strategy ID
        time_start: Backtest start time (ISO format string)
        time_end: Backtest end time (ISO format string)
        trading_stats: Dictionary containing trading statistics
        data_points: Number of data points used in backtest
        network: Network used (e.g., 'eth', 'bsc')
        token_symbol: Token symbol (e.g., 'ETH', 'BTC')
        timeframe: Timeframe used (e.g., '1d', '1h')
        
    Returns:
        BacktestHistoryDB: Created backtest history record
    """
    print(f"Creating backtest history for user {user_id}, strategy {strategy_id}")
    
    # Parse datetime strings
    start_dt = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
    
    # Extract key trading stats with defaults
    total_return = trading_stats.get('total_return', 0.0)
    avg_return = trading_stats.get('avg_return', 0.0)
    win_rate = trading_stats.get('win_rate', 0.0)
    total_trades = trading_stats.get('total_trades', 0)
    profitable_trades = trading_stats.get('profitable_trades', 0)
    
    backtest_history = BacktestHistoryDB(
        user_id=user_id,
        strategy_id=strategy_id,
        time_start=start_dt,
        time_end=end_dt,
        total_return=total_return,
        avg_return=avg_return,
        win_rate=win_rate,
        total_trades=total_trades,
        profitable_trades=profitable_trades,
        data_points=data_points,
        network=network,
        token_symbol=token_symbol,
        timeframe=timeframe,
        trading_stats_json=trading_stats
    )
    
    db.add(backtest_history)
    db.commit()
    db.refresh(backtest_history)
    
    print(f"Created backtest history with ID: {backtest_history.backtest_id}")
    return backtest_history

def get_backtest_histories_by_user(db: Session, user_id: int, limit: int = 50) -> List[BacktestHistoryDB]:
    """
    Get all backtest histories for a specific user
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of records to return
        
    Returns:
        List[BacktestHistoryDB]: List of backtest history records
    """
    print(f"Fetching backtest histories for user {user_id}")
    
    histories = db.query(BacktestHistoryDB)\
        .filter(BacktestHistoryDB.user_id == user_id)\
        .order_by(BacktestHistoryDB.created_at.desc())\
        .limit(limit)\
        .all()
    
    print(f"Found {len(histories)} backtest histories for user {user_id}")
    return histories

def get_backtest_histories_by_strategy(db: Session, strategy_id: int, limit: int = 20) -> List[BacktestHistoryDB]:
    """
    Get all backtest histories for a specific strategy
    
    Args:
        db: Database session
        strategy_id: Strategy ID
        limit: Maximum number of records to return
        
    Returns:
        List[BacktestHistoryDB]: List of backtest history records
    """
    print(f"Fetching backtest histories for strategy {strategy_id}")
    
    histories = db.query(BacktestHistoryDB)\
        .filter(BacktestHistoryDB.strategy_id == strategy_id)\
        .order_by(BacktestHistoryDB.created_at.desc())\
        .limit(limit)\
        .all()
    
    print(f"Found {len(histories)} backtest histories for strategy {strategy_id}")
    return histories

def get_backtest_history_by_id(db: Session, backtest_id: int) -> Optional[BacktestHistoryDB]:
    """
    Get a specific backtest history by ID
    
    Args:
        db: Database session
        backtest_id: Backtest history ID
        
    Returns:
        BacktestHistoryDB or None: Backtest history record
    """
    print(f"Fetching backtest history {backtest_id}")
    
    history = db.query(BacktestHistoryDB)\
        .filter(BacktestHistoryDB.backtest_id == backtest_id)\
        .first()
    
    if history:
        print(f"Found backtest history {backtest_id}")
    else:
        print(f"Backtest history {backtest_id} not found")
    
    return history

def delete_backtest_history(db: Session, backtest_id: int) -> bool:
    """
    Delete a backtest history record
    
    Args:
        db: Database session
        backtest_id: Backtest history ID
        
    Returns:
        bool: True if deleted, False if not found
    """
    print(f"Deleting backtest history {backtest_id}")
    
    history = get_backtest_history_by_id(db, backtest_id)
    if history:
        db.delete(history)
        db.commit()
        print(f"Deleted backtest history {backtest_id}")
        return True
    
    return False

def get_recent_backtest_histories(db: Session, user_id: int, limit: int = 10) -> List[BacktestHistoryDB]:
    """
    Get the most recent backtest histories for a user
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of records to return
        
    Returns:
        List[BacktestHistoryDB]: List of recent backtest history records
    """
    print(f"Fetching {limit} most recent backtest histories for user {user_id}")
    
    histories = db.query(BacktestHistoryDB)\
        .filter(BacktestHistoryDB.user_id == user_id)\
        .order_by(BacktestHistoryDB.created_at.desc())\
        .limit(limit)\
        .all()
    
    print(f"Found {len(histories)} recent backtest histories")
    return histories 