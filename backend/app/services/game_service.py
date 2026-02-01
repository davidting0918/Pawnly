from app.core.database import db_client
import secrets
import string

def generate_room_code(length=6):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

async def create_game(user_id: int):
    room_code = generate_room_code()
    query = "INSERT INTO games (room_code, white_player_id, status) VALUES ($1, $2, 'waiting') RETURNING *"
    new_game = await db_client.read_one(query, room_code, user_id)
    return new_game
