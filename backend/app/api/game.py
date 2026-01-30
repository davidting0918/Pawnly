from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.socket_manager import manager
import chess

router = APIRouter()

# In-memory game state for MVP (room_id -> chess.Board)
# In production, this should be in Redis or DB
games_cache = {}

@router.websocket("/ws/game/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    
    # Initialize game if not exists
    if room_id not in games_cache:
        games_cache[room_id] = chess.Board()
    
    board = games_cache[room_id]
    
    # Send initial state
    await websocket.send_json({
        "type": "init",
        "fen": board.fen(),
        "pgn": str(board.game()) if hasattr(board, 'game') else "" # python-chess board object doesn't store PGN natively like this usually
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            # Expected data: {"type": "move", "from": "e2", "to": "e4", "promotion": "q"}
            
            if data.get("type") == "move":
                try:
                    move = chess.Move.from_uci(f"{data['from']}{data['to']}")
                    
                    # Handle promotion (simple auto-queen for now if not specified)
                    if chess.square_rank(move.to_square) in [0, 7] and board.piece_type_at(move.from_square) == chess.PAWN:
                         move.promotion = chess.QUEEN

                    if move in board.legal_moves:
                        board.push(move)
                        
                        # Broadcast new state
                        await manager.broadcast({
                            "type": "update",
                            "fen": board.fen(),
                            "last_move": {
                                "from": data['from'],
                                "to": data['to']
                            },
                            "turn": "w" if board.turn == chess.WHITE else "b",
                            "check": board.is_check(),
                            "checkmate": board.is_checkmate(),
                            "game_over": board.is_game_over()
                        }, room_id)
                    else:
                        # Send error only to sender
                        await websocket.send_json({"type": "error", "message": "Illegal move"})
                        
                except ValueError:
                    await websocket.send_json({"type": "error", "message": "Invalid move format"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
