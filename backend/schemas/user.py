from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserPublic(BaseModel):
    id: int
    username: str
    elo_rating: int
    bot_elo: Optional[int] = None
    created_at: datetime
