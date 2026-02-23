from core.database import db_client
from typing import List, Dict, Any, Optional
import secrets
import string


def generate_room_code(length: int = 6) -> str:
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )


async def create_game(user_id: int, side: str = "white") -> Dict[str, Any]:
    """Create a new game. Creator picks white or black."""
    room_code = generate_room_code()
    if side == "black":
        query = """
            INSERT INTO games (room_code, black_player_id, status)
            VALUES ($1, $2, 'waiting')
            RETURNING *
        """
    else:
        query = """
            INSERT INTO games (room_code, white_player_id, status)
            VALUES ($1, $2, 'waiting')
            RETURNING *
        """
    return await db_client.execute_returning(query, room_code, user_id)


async def get_game_by_room_code(room_code: str) -> Optional[Dict[str, Any]]:
    return await db_client.read_one(
        "SELECT * FROM games WHERE room_code = $1", room_code
    )


async def get_game_by_id(game_id: int) -> Optional[Dict[str, Any]]:
    return await db_client.read_one(
        "SELECT * FROM games WHERE id = $1", game_id
    )


async def join_game(game_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Join the empty side of a waiting game. Works for either white or black vacancy."""
    # Try filling black side first
    query_black = """
        UPDATE games
        SET black_player_id = $1, status = 'active', updated_at = NOW()
        WHERE id = $2 AND status = 'waiting'
          AND black_player_id IS NULL AND white_player_id IS NOT NULL
          AND white_player_id != $1
        RETURNING *
    """
    result = await db_client.execute_returning(query_black, user_id, game_id)
    if result:
        return result

    # Try filling white side
    query_white = """
        UPDATE games
        SET white_player_id = $1, status = 'active', updated_at = NOW()
        WHERE id = $2 AND status = 'waiting'
          AND white_player_id IS NULL AND black_player_id IS NOT NULL
          AND black_player_id != $1
        RETURNING *
    """
    return await db_client.execute_returning(query_white, user_id, game_id)


async def update_game_state(
    game_id: int, fen: str, pgn: str, status: str = "active", winner_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    query = """
        UPDATE games
        SET fen = $1, pgn = $2, status = $3, winner_id = $4, updated_at = NOW()
        WHERE id = $5
        RETURNING *
    """
    return await db_client.execute_returning(query, fen, pgn, status, winner_id, game_id)


async def record_move(
    game_id: int, move_number: int, color: str, san: str, uci: str, fen_after: str
) -> Optional[Dict[str, Any]]:
    query = """
        INSERT INTO moves (game_id, move_number, color, san, uci, fen_after)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
    """
    return await db_client.execute_returning(
        query, game_id, move_number, color, san, uci, fen_after
    )


async def get_game_moves(game_id: int) -> List[Dict[str, Any]]:
    return await db_client.read(
        "SELECT * FROM moves WHERE game_id = $1 ORDER BY move_number", game_id
    )


async def abort_game(game_id: int) -> Optional[Dict[str, Any]]:
    query = """
        UPDATE games SET status = 'aborted', updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """
    return await db_client.execute_returning(query, game_id)
