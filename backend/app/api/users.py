from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.base import User, Game
from app.schemas.user import UserPublic
from app.schemas.game import GameSimple
from typing import List

router = APIRouter()

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged in user's profile.
    """
    return current_user

@router.get("/{user_id}/games", response_model=List[GameSimple])
async def read_user_games(user_id: int, db: AsyncSession = Depends(get_db), limit: int = 10):
    """
    Get a user's recent game history.
    """
    result = await db.execute(
        select(Game)
        .where((Game.white_player_id == user_id) | (Game.black_player_id == user_id))
        .order_by(Game.created_at.desc())
        .limit(limit)
        .options(selectinload(Game.white_player), selectinload(Game.black_player))
    )
    games = result.scalars().all()
    return games

@router.get("/leaderboard", response_model=List[UserPublic])
async def read_leaderboard(db: AsyncSession = Depends(get_db), limit: int = 10):
    """
    Get the top players by ELO rating.
    """
    result = await db.execute(
        select(User)
        .order_by(User.elo_rating.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return users
