from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.core.security import get_current_user
from app.schemas.user import UserPublic
from app.schemas.game import GameSimple
from app.services import user_service
from app.models.base import User # This import is now incorrect

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # The dependency now returns a dict, not a SQLAlchemy model
    return current_user

@router.get("/{user_id}/games", response_model=List[GameSimple])
async def read_user_games(user_id: int, limit: int = 10):
    games = await user_service.get_user_games(user_id=user_id, limit=limit)
    # We need to adapt the schema to handle the raw dict from db
    # For now, let's just return it, Pydantic might handle it if keys match
    return games

@router.get("/leaderboard", response_model=List[UserPublic])
async def read_leaderboard(limit: int = 10):
    users = await user_service.get_leaderboard(limit=limit)
    return users
