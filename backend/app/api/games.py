from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import string

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.base import User, Game
from app.schemas.game import GameResponse

router = APIRouter()

def generate_room_code(length=6):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

@router.post("/create", response_model=GameResponse)
async def create_game(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Create a new game room. The creator is assigned as White.
    """
    new_game = Game(
        room_code=generate_room_code(),
        white_player_id=current_user.id,
        status="waiting"
    )
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return new_game
