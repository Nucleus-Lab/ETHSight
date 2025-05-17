from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.user import get_user, create_user
from pydantic import BaseModel

router = APIRouter()

class UserResponse(BaseModel):
    user_id: int
    wallet_address: str

@router.post("/users/{wallet_address}", response_model=UserResponse)
async def get_or_create_user(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    user = get_user(db, wallet_address)
    if not user:
        user = create_user(db, wallet_address)
    return user