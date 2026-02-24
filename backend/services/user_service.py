from core.database import db_client
from typing import List, Dict, Any, Optional


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    return await db_client.read_one(
        "SELECT * FROM users WHERE id = $1", user_id
    )


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return await db_client.read_one(
        "SELECT * FROM users WHERE username = $1", username
    )


async def create_user(username: str, hashed_password: str) -> Dict[str, Any]:
    query = """
        INSERT INTO users (username, hashed_password)
        VALUES ($1, $2)
        RETURNING *
    """
    return await db_client.execute_returning(query, username, hashed_password)


async def get_user_games(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    query = """
        SELECT g.*,
               u_white.username AS white_username,
               u_white.elo_rating AS white_elo,
               u_black.username AS black_username,
               u_black.elo_rating AS black_elo
        FROM games g
        LEFT JOIN users u_white ON g.white_player_id = u_white.id
        LEFT JOIN users u_black ON g.black_player_id = u_black.id
        WHERE g.white_player_id = $1 OR g.black_player_id = $1
        ORDER BY g.created_at DESC
        LIMIT $2
    """
    return await db_client.read(query, user_id, limit)


async def get_leaderboard_with_bot_elo(limit: int = 10) -> List[Dict[str, Any]]:
    return await db_client.read(
        "SELECT id, username, elo_rating, bot_elo, created_at FROM users ORDER BY elo_rating DESC LIMIT $1",
        limit,
    )


async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    return await db_client.read(
        "SELECT id, username, elo_rating, created_at FROM users ORDER BY elo_rating DESC LIMIT $1",
        limit,
    )


async def update_elo(user_id: int, new_elo: int) -> None:
    await db_client.execute(
        "UPDATE users SET elo_rating = $1 WHERE id = $2", new_elo, user_id
    )


async def update_bot_elo(user_id: int, new_elo: int) -> None:
    await db_client.execute(
        "UPDATE users SET bot_elo = $1 WHERE id = $2", new_elo, user_id
    )


async def get_bot_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    return await db_client.read(
        "SELECT id, username, bot_elo FROM users ORDER BY bot_elo DESC LIMIT $1",
        limit,
    )
