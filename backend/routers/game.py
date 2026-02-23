from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
import chess

from core.security import get_current_user
from core.socket_manager import manager
from services import game_service

router = APIRouter()

# In-memory board cache: room_code -> chess.Board
boards_cache: Dict[str, chess.Board] = {}


@router.post("/games")
async def create_game(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Create a new game room. The creator plays white."""
    game = await game_service.create_game(current_user["id"])
    return {
        "id": game["id"],
        "room_code": game["room_code"],
        "status": game["status"],
    }


@router.post("/games/{room_code}/join")
async def join_game(room_code: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Join an existing game as black."""
    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Game is not waiting for players")
    if game["white_player_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot join your own game")

    updated = await game_service.join_game(game["id"], current_user["id"])
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to join game")

    return {
        "id": updated["id"],
        "room_code": updated["room_code"],
        "status": updated["status"],
    }


@router.get("/games/{room_code}")
async def get_game(room_code: str):
    """Get game state by room code."""
    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.websocket("/ws/game/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    """WebSocket endpoint for real-time chess gameplay."""
    # Verify game exists
    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        await websocket.close(code=4004, reason="Game not found")
        return

    await manager.connect(websocket, room_code)

    # Initialize board from DB state
    if room_code not in boards_cache:
        boards_cache[room_code] = chess.Board(game["fen"])

    board = boards_cache[room_code]

    # Send initial state
    await manager.send_personal(
        {
            "type": "init",
            "fen": board.fen(),
            "status": game["status"],
            "white_player_id": game["white_player_id"],
            "black_player_id": game["black_player_id"],
            "turn": "w" if board.turn == chess.WHITE else "b",
        },
        websocket,
    )

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "move":
                try:
                    uci_str = f"{data['from']}{data['to']}"
                    move = chess.Move.from_uci(uci_str)

                    # Handle pawn promotion
                    if (
                        chess.square_rank(move.to_square) in [0, 7]
                        and board.piece_type_at(move.from_square) == chess.PAWN
                    ):
                        promo = data.get("promotion", "q")
                        promo_map = {"q": chess.QUEEN, "r": chess.ROOK, "b": chess.BISHOP, "n": chess.KNIGHT}
                        move = chess.Move(move.from_square, move.to_square, promotion=promo_map.get(promo, chess.QUEEN))

                    if move not in board.legal_moves:
                        await manager.send_personal(
                            {"type": "error", "message": "Illegal move"}, websocket
                        )
                        continue

                    # Get SAN before pushing
                    san = board.san(move)
                    color = "w" if board.turn == chess.WHITE else "b"
                    move_number = board.fullmove_number

                    board.push(move)

                    # Determine game status
                    status = "active"
                    winner_id = None
                    if board.is_checkmate():
                        status = "finished"
                        # The side that just moved wins
                        game_data = await game_service.get_game_by_room_code(room_code)
                        winner_id = (
                            game_data["white_player_id"]
                            if color == "w"
                            else game_data["black_player_id"]
                        )
                    elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
                        status = "finished"  # draw

                    # Persist to DB
                    await game_service.update_game_state(
                        game["id"], board.fen(), board.board_fen(), status, winner_id
                    )
                    await game_service.record_move(
                        game["id"], move_number, color, san, move.uci(), board.fen()
                    )

                    # Broadcast to all in room
                    await manager.broadcast(
                        {
                            "type": "update",
                            "fen": board.fen(),
                            "last_move": {"from": data["from"], "to": data["to"], "san": san},
                            "turn": "w" if board.turn == chess.WHITE else "b",
                            "check": board.is_check(),
                            "checkmate": board.is_checkmate(),
                            "stalemate": board.is_stalemate(),
                            "game_over": board.is_game_over(),
                            "status": status,
                            "winner_id": winner_id,
                        },
                        room_code,
                    )

                    # Clean up cache if game over
                    if board.is_game_over():
                        boards_cache.pop(room_code, None)

                except ValueError:
                    await manager.send_personal(
                        {"type": "error", "message": "Invalid move format"}, websocket
                    )

            elif data.get("type") == "resign":
                game_data = await game_service.get_game_by_room_code(room_code)
                resigner_id = data.get("user_id")
                if resigner_id == game_data.get("white_player_id"):
                    winner_id = game_data.get("black_player_id")
                else:
                    winner_id = game_data.get("white_player_id")

                await game_service.update_game_state(
                    game["id"], board.fen(), board.board_fen(), "finished", winner_id
                )
                await manager.broadcast(
                    {
                        "type": "game_over",
                        "reason": "resign",
                        "winner_id": winner_id,
                        "fen": board.fen(),
                    },
                    room_code,
                )
                boards_cache.pop(room_code, None)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)
        # If room empty, clean up cache
        if manager.get_connection_count(room_code) == 0:
            boards_cache.pop(room_code, None)
