from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import chess

from app.core.database import get_db
from app.core.socket_manager import manager
from app.core.security import get_current_user
from app.models.base import User
from app.schemas.game import GameResponse
from app.services import game_service

router = APIRouter()

# --- REST API ---
@router.post("/games/create", response_model=GameResponse, tags=["games"])
async def create_new_game(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Create a new game room.
    """
    game = await game_service.create_game(db, user_id=current_user.id)
    return game

# --- WebSocket ---
# In-memory game state for MVP
games_cache = {}

@router.websocket("/ws/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    
    if room_id not in games_cache:
        games_cache[room_id] = chess.Board()
    
    board = games_cache[room_id]
    
    await websocket.send_json({"type": "init", "fen": board.fen()})
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "move":
                try:
                    move = chess.Move.from_uci(f"{data['from']}{data['to']}")
                    if chess.square_rank(move.to_square) in [0, 7] and board.piece_type_at(move.from_square) == chess.PAWN:
                         move.promotion = chess.QUEEN

                    if move in board.legal_moves:
                        board.push(move)
                        await manager.broadcast({"type": "update", "fen": board.fen()}, room_id)
                    else:
                        await websocket.send_json({"type": "error", "message": "Illegal move"})
                        
                except ValueError:
                    await websocket.send_json({"type": "error", "message": "Invalid move format"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
