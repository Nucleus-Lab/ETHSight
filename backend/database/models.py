from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Float
from sqlalchemy.orm import relationship
from backend.database import Base

class UserDB(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    canvases = relationship("CanvasDB", back_populates="user")
    strategies = relationship("StrategyDB", back_populates="user")
    backtest_histories = relationship("BacktestHistoryDB", back_populates="user")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "wallet_address": self.wallet_address,
            "created_at": self.created_at
        }

class CanvasDB(Base):
    __tablename__ = "canvases"

    canvas_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("UserDB", back_populates="canvases")
    messages = relationship("MessageDB", back_populates="canvas")
    visualizations = relationship("VisualizationDB", back_populates="canvas")
    signals = relationship("SignalDB", back_populates="canvas")

class MessageDB(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.canvas_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    text = Column(String)
    tool_results = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    canvas = relationship("CanvasDB", back_populates="messages")
    user = relationship("UserDB")

class VisualizationDB(Base):
    __tablename__ = "visualizations"

    visualization_id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.canvas_id"))
    json_data = Column(JSON)
    png_path = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    canvas = relationship("CanvasDB", back_populates="visualizations")

class SignalDB(Base):
    __tablename__ = "signals"
    
    signal_id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(Integer, ForeignKey("canvases.canvas_id"))
    signal_name = Column(String)
    signal_description = Column(Text)
    signal_code = Column(Text, nullable=True)  # Store the generated indicator code
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    canvas = relationship("CanvasDB", back_populates="signals")

class StrategyDB(Base):
    __tablename__ = "strategies"
    
    strategy_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    
    # Filter signal
    filter_signal_id = Column(Integer, ForeignKey("signals.signal_id"))
    
    # Buy condition
    buy_condition_signal_id = Column(Integer, ForeignKey("signals.signal_id"))
    buy_condition_operator = Column(String)
    buy_condition_threshold = Column(String)  # Using String to handle various number formats
    
    # Sell condition  
    sell_condition_signal_id = Column(Integer, ForeignKey("signals.signal_id"))
    sell_condition_operator = Column(String)
    sell_condition_threshold = Column(String)  # Using String to handle various number formats
    
    # Position parameters
    position_size = Column(String)  # Using String to handle various number formats
    max_position_value = Column(String)  # Using String to handle various number formats
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserDB", back_populates="strategies")
    filter_signal = relationship("SignalDB", foreign_keys=[filter_signal_id])
    buy_signal = relationship("SignalDB", foreign_keys=[buy_condition_signal_id])
    sell_signal = relationship("SignalDB", foreign_keys=[sell_condition_signal_id])
    backtest_histories = relationship("BacktestHistoryDB", back_populates="strategy")

    def to_dict(self):
        return {
            "strategy_id": self.strategy_id,
            "user_id": self.user_id,
            "filter_signal_id": self.filter_signal_id,
            "buy_condition_signal_id": self.buy_condition_signal_id,
            "buy_condition_operator": self.buy_condition_operator,
            "buy_condition_threshold": self.buy_condition_threshold,
            "sell_condition_signal_id": self.sell_condition_signal_id,
            "sell_condition_operator": self.sell_condition_operator,
            "sell_condition_threshold": self.sell_condition_threshold,
            "position_size": self.position_size,
            "max_position_value": self.max_position_value,
            "created_at": self.created_at
        }

class BacktestHistoryDB(Base):
    __tablename__ = "backtest_histories"
    
    backtest_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    strategy_id = Column(Integer, ForeignKey("strategies.strategy_id"))
    
    # Backtest time range
    time_start = Column(DateTime)
    time_end = Column(DateTime)
    
    # Trading statistics
    total_return = Column(Float)
    avg_return = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)
    profitable_trades = Column(Integer)
    
    # Additional backtest metadata
    data_points = Column(Integer)
    network = Column(String)
    token_symbol = Column(String)
    timeframe = Column(String)
    
    # Store complete trading stats as JSON for flexibility
    trading_stats_json = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserDB", back_populates="backtest_histories")
    strategy = relationship("StrategyDB", back_populates="backtest_histories")

    def to_dict(self):
        return {
            "backtest_id": self.backtest_id,
            "user_id": self.user_id,
            "strategy_id": self.strategy_id,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "total_return": self.total_return,
            "avg_return": self.avg_return,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profitable_trades": self.profitable_trades,
            "data_points": self.data_points,
            "network": self.network,
            "token_symbol": self.token_symbol,
            "timeframe": self.timeframe,
            "trading_stats_json": self.trading_stats_json,
            "created_at": self.created_at
        } 