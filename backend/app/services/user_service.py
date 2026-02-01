from app.core.database import db_client
from typing import List, Dict, Any, Optional

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    return await db_client.read_one("SELECT * FROM users WHERE id = $1", user_id)

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return await db_client.read_one("SELECT * FROM users WHERE username = $1", username)

async def create_user(username: str, hashed_password: str) -> Dict[str, Any]:
    query = "INSERT INTO users (username, hashed_password) VALUES ($1, $2) RETURNING *"
    result = await db_client.read_one(query, username, hashed_password)
    return result

async def get_user_games(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    # This query needs a JOIN to be useful, for now just get raw data
    query = """
        SELECT g.*, u_white.username as white_username, u_black.username as black_username
        FROM games g
        LEFT JOIN users u_white ON g.white_player_id = u_white.id
        LEFT JOIN users u_black ON g.black_player_id = u_black.id
        WHERE g.white_player_id = $1 OR g.black_player_id = $1
        ORDER BY g.created_at DESC
        LIMIT $2
    """
    return await db_client.read(query, user_id, limit)

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    return await db_client.read("SELECT id, username, elo_rating, created_at FROM users ORDER BY elo_rating DESC LIMIT $1", limit)
