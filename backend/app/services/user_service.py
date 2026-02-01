from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.base import User, Game

async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, hashed_password: str):
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def get_user_games(db: AsyncSession, user_id: int, limit: int = 10):
    result = await db.execute(
        select(Game)
        .where((Game.white_player_id == user_id) | (Game.black_player_id == user_id))
        .order_by(Game.created_at.desc())
        .limit(limit)
        .options(selectinload(Game.white_player), selectinload(Game.black_player))
    )
    return result.scalars().all()

async def get_leaderboard(db: AsyncSession, limit: int = 10):
    result = await db.execute(
        select(User)
        .order_by(User.elo_rating.desc())
        .limit(limit)
    )
    return result.scalars().all()
