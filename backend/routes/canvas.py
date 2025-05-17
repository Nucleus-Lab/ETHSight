from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database.user import get_user
from backend.database.canvas import get_canvases_for_user

from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Models for request/response
class CanvasResponse(BaseModel):
    canvas_id: int
    user_id: int
    created_at: datetime

@router.get("/canvas/user/{wallet_address}", response_model=List[CanvasResponse])
async def get_user_canvas_list(
    wallet_address: str,
    db: Session = Depends(get_db)
):
    user = get_user(db, wallet_address)
    print("user", user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    canvases = get_canvases_for_user(db, user.user_id)
    print("canvases", canvases)
    return canvases









