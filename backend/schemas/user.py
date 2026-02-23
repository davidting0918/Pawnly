from pydantic import BaseModel
from datetime import datetime


class UserPublic(BaseModel):
    id: int
    username: str
    elo_rating: int
    created_at: datetime
