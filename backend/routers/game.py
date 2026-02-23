from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import chess

from core.security import get_current_user
from core.socket_manager import manager
from services import game_service

router = APIRouter()

boards_cache: Dict[str, chess.Board] = {}
turn_start_cache: Dict[str, str] = {}


class CreateGameRequest(BaseModel):
    side: str = "white"
    time_per_move: Optional[int] = None


@router.post("/games")
async def create_game(
    body: CreateGameRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if body.side not in ("white", "black"):
        raise HTTPException(status_code=400, detail="side must be 'white' or 'black'")

    game = await game_service.create_game(
        current_user["id"], side=body.side, time_per_move=body.time_per_move
    )
    return {
        "id": game["id"],
        "room_code": game["room_code"],
        "status": game["status"],
        "side": body.side,
        "time_per_move": game.get("time_per_move"),
    }


@router.post("/games/{room_code}/join")
async def join_game(room_code: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Game is not waiting for players")
    if game["white_player_id"] == current_user["id"] or game["black_player_id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot join your own game")

    updated = await game_service.join_game(game["id"], current_user["id"])
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to join game")

    joined_side = "white" if updated["white_player_id"] == current_user["id"] else "black"
    return {
        "id": updated["id"],
        "room_code": updated["room_code"],
        "status": updated["status"],
        "side": joined_side,
    }


@router.get("/games/{room_code}")
async def get_game(room_code: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    uid = current_user["id"]
    if uid != game["white_player_id"] and uid != game["black_player_id"]:
        raise HTTPException(status_code=403, detail="You are not a player in this game")

    return game


@router.websocket("/ws/game/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    await websocket.accept()

    try:
        auth_msg = await websocket.receive_json()
        if auth_msg.get("type") != "auth" or "user_id" not in auth_msg:
            await websocket.send_json({"type": "error", "message": "First message must be auth with user_id"})
            await websocket.close(code=4001, reason="Auth required")
            return
        ws_user_id = auth_msg["user_id"]
    except Exception:
        await websocket.close(code=4001, reason="Auth required")
        return

    game = await game_service.get_game_by_room_code(room_code)
    if not game:
        await websocket.send_json({"type": "error", "message": "Game not found"})
        await websocket.close(code=4004, reason="Game not found")
        return

    if ws_user_id != game["white_player_id"] and ws_user_id != game["black_player_id"]:
        await websocket.send_json({"type": "error", "message": "You are not a player in this game"})
        await websocket.close(code=4003, reason="Not a player")
        return

    player_side = "w" if ws_user_id == game["white_player_id"] else "b"

    if room_code not in manager.active_connections:
        manager.active_connections[room_code] = []
    manager.active_connections[room_code].append(websocket)

    if room_code not in boards_cache:
        boards_cache[room_code] = chess.Board(game["fen"])
    board = boards_cache[room_code]

    players = await game_service.get_game_players(game)
    existing_moves = await game_service.get_game_moves(game["id"])
    move_list = [
        {"move_number": m["move_number"], "color": m["color"], "san": m["san"]}
        for m in existing_moves
    ]

    time_per_move = game.get("time_per_move")
    turn_started_at = turn_start_cache.get(room_code)
    if not turn_started_at and game["status"] == "active":
        turn_started_at = datetime.now(timezone.utc).isoformat()
        turn_start_cache[room_code] = turn_started_at

    await websocket.send_json({
        "type": "init",
        "fen": board.fen(),
        "status": game["status"],
        "white_player_id": game["white_player_id"],
        "black_player_id": game["black_player_id"],
        "your_side": player_side,
        "turn": "w" if board.turn == chess.WHITE else "b",
        "players": players,
        "moves": move_list,
        "time_per_move": time_per_move,
        "turn_started_at": turn_started_at,
    })

    if game["status"] == "active" and manager.get_connection_count(room_code) >= 2:
        now_iso = datetime.now(timezone.utc).isoformat()
        if room_code not in turn_start_cache:
            turn_start_cache[room_code] = now_iso

        await manager.broadcast(
            {
                "type": "game_start",
                "fen": board.fen(),
                "status": "active",
                "white_player_id": game["white_player_id"],
                "black_player_id": game["black_player_id"],
                "turn": "w" if board.turn == chess.WHITE else "b",
                "players": players,
                "time_per_move": time_per_move,
                "turn_started_at": turn_start_cache[room_code],
            },
            room_code,
        )

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "move":
                current_turn = "w" if board.turn == chess.WHITE else "b"
                if player_side != current_turn:
                    await websocket.send_json({"type": "error", "message": "Not your turn"})
                    continue

                try:
                    uci_str = f"{data['from']}{data['to']}"
                    move = chess.Move.from_uci(uci_str)

                    if (
                        chess.square_rank(move.to_square) in [0, 7]
                        and board.piece_type_at(move.from_square) == chess.PAWN
                    ):
                        promo = data.get("promotion", "q")
                        promo_map = {"q": chess.QUEEN, "r": chess.ROOK, "b": chess.BISHOP, "n": chess.KNIGHT}
                        move = chess.Move(move.from_square, move.to_square, promotion=promo_map.get(promo, chess.QUEEN))

                    if move not in board.legal_moves:
                        await websocket.send_json({"type": "error", "message": "Illegal move"})
                        continue

                    san = board.san(move)
                    color = "w" if board.turn == chess.WHITE else "b"
                    move_number = board.fullmove_number

                    board.push(move)

                    status = "active"
                    winner_id = None
                    if board.is_checkmate():
                        status = "finished"
                        game_data = await game_service.get_game_by_room_code(room_code)
                        winner_id = (
                            game_data["white_player_id"]
                            if color == "w"
                            else game_data["black_player_id"]
                        )
                    elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
                        status = "finished"

                    await game_service.update_game_state(
                        game["id"], board.fen(), board.board_fen(), status, winner_id
                    )
                    await game_service.record_move(
                        game["id"], move_number, color, san, move.uci(), board.fen()
                    )

                    now_iso = datetime.now(timezone.utc).isoformat()
                    turn_start_cache[room_code] = now_iso

                    await manager.broadcast(
                        {
                            "type": "update",
                            "fen": board.fen(),
                            "last_move": {
                                "from": data["from"],
                                "to": data["to"],
                                "san": san,
                                "color": color,
                                "move_number": move_number,
                            },
                            "turn": "w" if board.turn == chess.WHITE else "b",
                            "check": board.is_check(),
                            "checkmate": board.is_checkmate(),
                            "stalemate": board.is_stalemate(),
                            "game_over": board.is_game_over(),
                            "status": status,
                            "winner_id": winner_id,
                            "turn_started_at": now_iso,
                            "time_per_move": time_per_move,
                        },
                        room_code,
                    )

                    if board.is_game_over():
                        boards_cache.pop(room_code, None)
                        turn_start_cache.pop(room_code, None)

                except ValueError:
                    await websocket.send_json({"type": "error", "message": "Invalid move format"})

            elif data.get("type") == "timeout":
                if not time_per_move:
                    continue
                ts = turn_start_cache.get(room_code)
                if not ts:
                    continue
                elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
                if elapsed < time_per_move - 1:
                    continue

                current_turn = "w" if board.turn == chess.WHITE else "b"
                game_data = await game_service.get_game_by_room_code(room_code)
                if current_turn == "w":
                    winner_id = game_data.get("black_player_id")
                else:
                    winner_id = game_data.get("white_player_id")

                await game_service.update_game_state(
                    game["id"], board.fen(), board.board_fen(), "finished", winner_id
                )
                await manager.broadcast(
                    {
                        "type": "game_over",
                        "reason": "timeout",
                        "winner_id": winner_id,
                        "fen": board.fen(),
                    },
                    room_code,
                )
                boards_cache.pop(room_code, None)
                turn_start_cache.pop(room_code, None)

            elif data.get("type") == "resign":
                game_data = await game_service.get_game_by_room_code(room_code)
                if player_side == "w":
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
                turn_start_cache.pop(room_code, None)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)
        if manager.get_connection_count(room_code) == 0:
            boards_cache.pop(room_code, None)
            turn_start_cache.pop(room_code, None)
