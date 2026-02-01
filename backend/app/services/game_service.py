from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import string

from app.models.base import Game

def generate_room_code(length=6):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

async def create_game(db: AsyncSession, user_id: int):
    new_game = Game(
        room_code=generate_room_code(),
        white_player_id=user_id,
        status="waiting"
    )
    db.add(new_game)
    await db.commit()
    await db.refresh(new_game)
    return new_game
