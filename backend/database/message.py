import os
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from backend.database import get_db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from backend.database.models import MessageDB

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()


# Database operations for message
def create_message(db, canvas_id: int, user_id: int, text: str):
    new_message = MessageDB(
        canvas_id=canvas_id,
        user_id=user_id,
        text=text,
        created_at=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message

def get_messages_for_canvas(db, canvas_id: int):
    return db.query(MessageDB)\
        .filter(MessageDB.canvas_id == canvas_id)\
        .order_by(MessageDB.created_at.asc())\
        .all()
        
def get_message_by_id(db, message_id: int):
    return db.query(MessageDB)\
        .filter(MessageDB.message_id == message_id)\
        .first()

