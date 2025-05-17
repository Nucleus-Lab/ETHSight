from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, DateTime, text, ForeignKey
from sqlalchemy.exc import IntegrityError
from backend.database.models import CanvasDB

# Database operations for canvas
def create_canvas(db, user_id: int):
    try:
        new_canvas = CanvasDB(user_id=user_id)
        db.add(new_canvas)
        db.commit()
        db.refresh(new_canvas)
        return new_canvas
    except IntegrityError:
        db.rollback()
        raise Exception("Failed to create canvas")
    
def get_canvas(db, canvas_id: int):
    return db.query(CanvasDB).filter(CanvasDB.canvas_id == canvas_id).first()

def get_canvases_for_user(db, user_id: int):
    return db.query(CanvasDB).filter(CanvasDB.user_id == user_id).all()