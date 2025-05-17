from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class UserDB(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    canvases = relationship("CanvasDB", back_populates="user")

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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    canvas = relationship("CanvasDB", back_populates="signals") 