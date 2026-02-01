from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import chess

from app.core.security import get_current_user
from app.schemas.game import GameResponse
from app.services import game_service

router = APIRouter()

# --- REST API ---
@router.post("/games/create", response_model=GameResponse, tags=["games"])
async def create_new_game(current_user: dict = Depends(get_current_user)):
    game = await game_service.create_game(user_id=current_user['id'])
    return game

# --- WebSocket ---
# ... (WebSocket part remains the same as it doesn't touch DB directly)
games_cache = {}

@router.websocket("/ws/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    # ... (rest of the function is omitted for brevity as it's unchanged)
