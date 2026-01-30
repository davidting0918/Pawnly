from pydantic import BaseModel
from datetime import datetime
from .user import UserPublic

class GameSimple(BaseModel):
    id: int
    status: str
    winner_id: int | None
    created_at: datetime
    white_player: UserPublic | None
    black_player: UserPublic | None

    class Config:
        from_attributes = True
