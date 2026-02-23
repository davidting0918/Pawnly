from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException

from core.security import get_current_user
from schemas.user import UserPublic
from schemas.game import GameSimple
from services import user_service

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current logged-in user's profile."""
    return UserPublic(
        id=current_user["id"],
        username=current_user["username"],
        elo_rating=current_user["elo_rating"],
        created_at=current_user["created_at"],
    )


@router.get("/{user_id}/games")
async def read_user_games(user_id: int, limit: int = 10):
    """Get a user's recent game history."""
    rows = await user_service.get_user_games(user_id, limit)

    results = []
    for row in rows:
        white = None
        if row.get("white_player_id"):
            white = UserPublic(
                id=row["white_player_id"],
                username=row.get("white_username", ""),
                elo_rating=row.get("white_elo", 1200),
                created_at=row["created_at"],
            )
        black = None
        if row.get("black_player_id"):
            black = UserPublic(
                id=row["black_player_id"],
                username=row.get("black_username", ""),
                elo_rating=row.get("black_elo", 1200),
                created_at=row["created_at"],
            )
        results.append(
            GameSimple(
                id=row["id"],
                room_code=row.get("room_code"),
                status=row["status"],
                winner_id=row.get("winner_id"),
                created_at=row["created_at"],
                white_player=white,
                black_player=black,
            )
        )
    return results


@router.get("/leaderboard", response_model=List[UserPublic])
async def read_leaderboard(limit: int = 10):
    """Get the top players by ELO rating."""
    rows = await user_service.get_leaderboard(limit)
    return [
        UserPublic(
            id=r["id"],
            username=r["username"],
            elo_rating=r["elo_rating"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
