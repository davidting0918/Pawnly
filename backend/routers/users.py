from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

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
        bot_elo=current_user.get("bot_elo", 1200),
        created_at=current_user["created_at"],
    )


@router.get("/{user_id}/games")
async def read_user_games(
    user_id: int,
    limit: int = 10,
    game_type: Optional[str] = Query(None, alias="type"),
):
    """Get a user's recent game history. ?type=bot for bot games only, ?type=human for human only."""
    rows = await user_service.get_user_games(user_id, limit)

    results = []
    for row in rows:
        is_bot = row.get("is_bot_game", False)

        # Filter by game type if specified
        if game_type == "bot" and not is_bot:
            continue
        if game_type == "human" and is_bot:
            continue

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
                is_bot_game=is_bot,
                bot_difficulty=row.get("bot_difficulty"),
                created_at=row["created_at"],
                white_player=white,
                black_player=black,
            )
        )
    return results


@router.get("/leaderboard", response_model=List[UserPublic])
async def read_leaderboard(
    limit: int = 10,
    board_type: Optional[str] = Query(None, alias="type"),
):
    """Get the top players by ELO rating. ?type=bot for bot Elo leaderboard."""
    if board_type == "bot":
        rows = await user_service.get_bot_leaderboard(limit)
        return [
            UserPublic(
                id=r["id"],
                username=r["username"],
                elo_rating=r.get("elo_rating", 1200),
                bot_elo=r.get("bot_elo", 1200),
                created_at=r.get("created_at"),
            )
            for r in rows
        ]

    rows = await user_service.get_leaderboard(limit)
    return [
        UserPublic(
            id=r["id"],
            username=r["username"],
            elo_rating=r["elo_rating"],
            bot_elo=r.get("bot_elo", 1200),
            created_at=r["created_at"],
        )
        for r in rows
    ]
