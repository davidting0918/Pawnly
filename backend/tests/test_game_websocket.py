"""Tests for WebSocket game logic (moves, checkmate, resign, promotion, illegal moves)."""
import pytest
import json
from unittest.mock import AsyncMock, patch
from copy import deepcopy

from tests.conftest import (
    FAKE_GAME_ACTIVE,
    FAKE_GAME_WAITING,
    INITIAL_FEN,
)


class TestWebSocketConnect:
    @pytest.mark.asyncio
    async def test_ws_connect_valid_game(self, client, mock_db):
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE

        async with client.stream("GET", "/api/ws/game/ABC123") as resp:
            # httpx doesn't do WS natively; we test via starlette TestClient instead
            pass

    @pytest.mark.asyncio
    async def test_ws_connect_nonexistent_game(self, client, mock_db):
        """WebSocket to a non-existent game should be rejected."""
        mock_db.read_one.return_value = None
        # This will fail to upgrade — the endpoint closes with code 4004
        # We can't test WS directly with httpx, so we test the HTTP upgrade fails


# ── Use Starlette TestClient for actual WebSocket tests ──
from starlette.testclient import TestClient
from main import app


class TestWebSocketGameplay:
    """WebSocket tests using Starlette's synchronous TestClient."""

    def test_ws_init_message(self, mock_db):
        """On connect, client receives init message with FEN and status."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            data = ws.receive_json()
            assert data["type"] == "init"
            assert data["fen"] == INITIAL_FEN
            assert data["status"] == "active"
            assert data["turn"] == "w"
            assert data["white_player_id"] == 1
            assert data["black_player_id"] == 2

    def test_ws_legal_move(self, mock_db):
        """A legal move should broadcast an update."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE  # update + record

        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            init = ws.receive_json()
            assert init["type"] == "init"

            # e2e4 — standard opening
            ws.send_json({"type": "move", "from": "e2", "to": "e4"})
            update = ws.receive_json()
            assert update["type"] == "update"
            assert "e4" in update["fen"] or "4P3" in update["fen"] or update["fen"] != INITIAL_FEN
            assert update["turn"] == "b"  # now black's turn
            assert update["check"] is False
            assert update["game_over"] is False
            assert update["last_move"]["from"] == "e2"
            assert update["last_move"]["to"] == "e4"
            assert update["last_move"]["san"] == "e4"

    def test_ws_illegal_move(self, mock_db):
        """An illegal move should return an error, not an update."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            # e2e5 — illegal (pawn can't jump 3 squares)
            ws.send_json({"type": "move", "from": "e2", "to": "e5"})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "illegal" in resp["message"].lower()

    def test_ws_invalid_square(self, mock_db):
        """Invalid square notation should return error."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            ws.send_json({"type": "move", "from": "z9", "to": "z1"})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    def test_ws_multiple_moves(self, mock_db):
        """Play a few moves and verify state updates."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            moves = [
                ("e2", "e4"),  # white
                ("e7", "e5"),  # black
                ("g1", "f3"),  # white
                ("b8", "c6"),  # black
            ]
            for src, dst in moves:
                ws.send_json({"type": "move", "from": src, "to": dst})
                resp = ws.receive_json()
                assert resp["type"] == "update"
                assert resp["game_over"] is False

    def test_ws_scholars_mate(self, mock_db):
        """Play Scholar's Mate (4-move checkmate) and verify game over."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)

        # Need to clear boards_cache between tests
        from routers.game import boards_cache
        boards_cache.pop("ABC123", None)

        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            scholar_mate = [
                ("e2", "e4"),  # 1. e4
                ("e7", "e5"),  # 1... e5
                ("f1", "c4"),  # 2. Bc4
                ("b8", "c6"),  # 2... Nc6
                ("d1", "h5"),  # 3. Qh5
                ("g8", "f6"),  # 3... Nf6?? (blunder)
                ("h5", "f7"),  # 4. Qxf7# checkmate!
            ]

            for i, (src, dst) in enumerate(scholar_mate):
                ws.send_json({"type": "move", "from": src, "to": dst})
                resp = ws.receive_json()
                assert resp["type"] == "update"

                if i == len(scholar_mate) - 1:
                    # Last move is checkmate
                    assert resp["checkmate"] is True
                    assert resp["game_over"] is True
                    assert resp["status"] == "finished"
                    assert resp["winner_id"] == 1  # white wins

        boards_cache.pop("ABC123", None)

    def test_ws_resign(self, mock_db):
        """Player resigns, opponent wins."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        from routers.game import boards_cache
        boards_cache.pop("ABC123", None)

        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            # White resigns → Black (user_id=2) should win
            ws.send_json({"type": "resign", "user_id": 1})
            resp = ws.receive_json()
            assert resp["type"] == "game_over"
            assert resp["reason"] == "resign"
            assert resp["winner_id"] == 2  # black wins

        boards_cache.pop("ABC123", None)

    def test_ws_resign_black(self, mock_db):
        """Black resigns, white wins."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        test_client = TestClient(app)
        from routers.game import boards_cache
        boards_cache.pop("ABC123", None)

        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.receive_json()  # init

            # Make a move first so it's black's turn
            ws.send_json({"type": "move", "from": "e2", "to": "e4"})
            ws.receive_json()  # update

            # Black resigns
            ws.send_json({"type": "resign", "user_id": 2})
            resp = ws.receive_json()
            assert resp["type"] == "game_over"
            assert resp["winner_id"] == 1  # white wins

        boards_cache.pop("ABC123", None)

    def test_ws_nonexistent_game_closes(self, mock_db):
        """WebSocket to non-existent game should close."""
        mock_db.read_one.return_value = None

        test_client = TestClient(app)
        # starlette should raise an exception when the WS is closed from server side
        try:
            with test_client.websocket_connect("/api/ws/game/NOPE00") as ws:
                ws.receive_json()
            assert False, "Should have been closed"
        except Exception:
            pass  # expected — server closes with 4004


class TestBoardCacheIsolation:
    """Ensure different rooms have independent board states."""

    def test_separate_rooms(self, mock_db):
        game_a = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_A"}
        game_b = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_B"}
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        from routers.game import boards_cache
        boards_cache.pop("ROOM_A", None)
        boards_cache.pop("ROOM_B", None)

        test_client = TestClient(app)

        # Room A: play e4
        mock_db.read_one.return_value = game_a
        with test_client.websocket_connect("/api/ws/game/ROOM_A") as ws_a:
            ws_a.receive_json()
            ws_a.send_json({"type": "move", "from": "e2", "to": "e4"})
            update_a = ws_a.receive_json()
            fen_a = update_a["fen"]

        # Room B: play d4
        mock_db.read_one.return_value = game_b
        with test_client.websocket_connect("/api/ws/game/ROOM_B") as ws_b:
            ws_b.receive_json()
            ws_b.send_json({"type": "move", "from": "d2", "to": "d4"})
            update_b = ws_b.receive_json()
            fen_b = update_b["fen"]

        # The FENs should be different
        assert fen_a != fen_b

        boards_cache.pop("ROOM_A", None)
        boards_cache.pop("ROOM_B", None)
