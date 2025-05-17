from datetime import datetime
from typing import List
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.exc import IntegrityError
from backend.database.models import UserDB

# Database operations for user
def create_user(db, wallet_address: str):
    try:
        new_user = UserDB(wallet_address=wallet_address)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise Exception("Failed to create user")

def get_user(db, wallet_address: str):
    return db.query(UserDB).filter(UserDB.wallet_address == wallet_address).first()