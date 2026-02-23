from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from schemas.user import UserPublic


class GameSimple(BaseModel):
    id: int
    room_code: Optional[str] = None
    status: str
    winner_id: Optional[int] = None
    created_at: datetime
    white_player: Optional[UserPublic] = None
    black_player: Optional[UserPublic] = None


class GameDetail(BaseModel):
    id: int
    room_code: Optional[str] = None
    white_player_id: Optional[int] = None
    black_player_id: Optional[int] = None
    fen: str
    pgn: str
    status: str
    winner_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
