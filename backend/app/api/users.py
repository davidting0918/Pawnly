from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.base import User
from app.schemas.user import UserPublic
from app.schemas.game import GameSimple
from app.services import user_service

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/{user_id}/games", response_model=List[GameSimple])
async def read_user_games(user_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    games = await user_service.get_user_games(db, user_id=user_id, limit=limit)
    return games

@router.get("/leaderboard", response_model=List[UserPublic])
async def read_leaderboard(db: AsyncSession = Depends(get_db), limit: int = 10):
    users = await user_service.get_leaderboard(db, limit=limit)
    return users
