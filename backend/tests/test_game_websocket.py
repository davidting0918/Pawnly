"""Tests for WebSocket game logic (moves, checkmate, resign, turn enforcement, auth)."""
import pytest
import json
from unittest.mock import AsyncMock, patch
from copy import deepcopy

from tests.conftest import (
    FAKE_GAME_ACTIVE,
    FAKE_GAME_WAITING,
    INITIAL_FEN,
)

# ── Use Starlette TestClient for WebSocket tests ──
from starlette.testclient import TestClient
from main import app


class WSSession:
    """Context-managed WebSocket test session with auth."""
    def __init__(self, test_client, room_code, user_id, mock_db, game_data):
        mock_db.read_one.return_value = game_data
        self._ctx = test_client.websocket_connect(f"/api/ws/game/{room_code}")
        self._user_id = user_id
        self.ws = None
        self.init_data = None

    def __enter__(self):
        self.ws = self._ctx.__enter__()
        self.ws.send_json({"type": "auth", "user_id": self._user_id})
        self.init_data = self.ws.receive_json()
        return self

    def __exit__(self, *args):
        return self._ctx.__exit__(*args)

    def send_json(self, data):
        self.ws.send_json(data)

    def receive_json(self):
        return self.ws.receive_json()


class TestWebSocketAuth:
    def test_ws_no_auth_message_closes(self, mock_db):
        """WS without auth message should be rejected."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            # Send a move instead of auth
            ws.send_json({"type": "move", "from": "e2", "to": "e4"})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    def test_ws_non_player_rejected(self, mock_db):
        """User who is not a player should be rejected."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE  # white=1, black=2
        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.send_json({"type": "auth", "user_id": 999})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "not a player" in resp["message"].lower()

    def test_ws_nonexistent_game(self, mock_db):
        """WS to non-existent game should close."""
        mock_db.read_one.return_value = None
        test_client = TestClient(app)
        with test_client.websocket_connect("/api/ws/game/NOPE00") as ws:
            ws.send_json({"type": "auth", "user_id": 1})
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestWebSocketGameplay:
    def _setup(self, mock_db):
        from routers.game import boards_cache
        boards_cache.pop("ABC123", None)
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

    def _cleanup(self):
        from routers.game import boards_cache
        boards_cache.pop("ABC123", None)

    def test_ws_init_message(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            assert s.init_data["type"] == "init"
            assert s.init_data["fen"] == INITIAL_FEN
            assert s.init_data["status"] == "active"
            assert s.init_data["your_side"] == "w"
            assert s.init_data["turn"] == "w"
        self._cleanup()

    def test_ws_init_black_side(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 2, mock_db, FAKE_GAME_ACTIVE) as s:
            assert s.init_data["your_side"] == "b"
        self._cleanup()

    def test_ws_legal_move(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "move", "from": "e2", "to": "e4"})
            update = s.receive_json()
            assert update["type"] == "update"
            assert update["turn"] == "b"
            assert update["game_over"] is False
            assert update["last_move"]["san"] == "e4"
        self._cleanup()

    def test_ws_wrong_turn_rejected(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 2, mock_db, FAKE_GAME_ACTIVE) as s:
            assert s.init_data["your_side"] == "b"
            s.send_json({"type": "move", "from": "e7", "to": "e5"})
            resp = s.receive_json()
            assert resp["type"] == "error"
            assert "not your turn" in resp["message"].lower()
        self._cleanup()

    def test_ws_illegal_move(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "move", "from": "e2", "to": "e5"})
            resp = s.receive_json()
            assert resp["type"] == "error"
            assert "illegal" in resp["message"].lower()
        self._cleanup()

    def test_ws_invalid_square(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "move", "from": "z9", "to": "z1"})
            resp = s.receive_json()
            assert resp["type"] == "error"
        self._cleanup()

    def test_ws_resign_white(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "resign"})
            resp = s.receive_json()
            assert resp["type"] == "game_over"
            assert resp["reason"] == "resign"
            assert resp["winner_id"] == 2
        self._cleanup()

    def test_ws_resign_black(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 2, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "resign"})
            resp = s.receive_json()
            assert resp["type"] == "game_over"
            assert resp["winner_id"] == 1
        self._cleanup()


class TestBoardCacheIsolation:
    def test_separate_rooms(self, mock_db):
        game_a = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_A"}
        game_b = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_B"}
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        from routers.game import boards_cache
        boards_cache.pop("ROOM_A", None)
        boards_cache.pop("ROOM_B", None)

        tc = TestClient(app)
        with WSSession(tc, "ROOM_A", 1, mock_db, game_a) as sa:
            sa.send_json({"type": "move", "from": "e2", "to": "e4"})
            fen_a = sa.receive_json()["fen"]

        with WSSession(tc, "ROOM_B", 1, mock_db, game_b) as sb:
            sb.send_json({"type": "move", "from": "d2", "to": "d4"})
            fen_b = sb.receive_json()["fen"]

        assert fen_a != fen_b
        boards_cache.pop("ROOM_A", None)
        boards_cache.pop("ROOM_B", None)
