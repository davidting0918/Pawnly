"""Tests for WebSocket game logic (moves, checkmate, resign, turn enforcement, auth, timeout)."""
import pytest
import json
from unittest.mock import AsyncMock, patch
from copy import deepcopy

from tests.conftest import (
    FAKE_USER_WHITE,
    FAKE_USER_BLACK,
    FAKE_GAME_ACTIVE,
    FAKE_GAME_WAITING,
    INITIAL_FEN,
)

from starlette.testclient import TestClient
from main import app

USER_MAP = {
    1: {"id": 1, "username": "alice@example.com"},
    2: {"id": 2, "username": "bob@example.com"},
}


class WSSession:
    """Context-managed WebSocket test session with auth."""
    def __init__(self, test_client, room_code, user_id, mock_db, game_data):
        self._game_data = game_data

        def read_one_router(query, *args):
            if "games" in query:
                return game_data
            if "users" in query:
                uid = args[0] if args else None
                return USER_MAP.get(uid)
            return None

        mock_db.read_one.side_effect = read_one_router
        mock_db.read.return_value = []

        self._ctx = test_client.websocket_connect(f"/api/ws/game/{room_code}")
        self._user_id = user_id
        self._mock_db = mock_db
        self.ws = None
        self.init_data = None

    def __enter__(self):
        self.ws = self._ctx.__enter__()
        self.ws.send_json({"type": "auth", "user_id": self._user_id})
        self.init_data = self.ws.receive_json()
        return self

    def __exit__(self, *args):
        self._mock_db.read_one.side_effect = None
        return self._ctx.__exit__(*args)

    def send_json(self, data):
        self.ws.send_json(data)

    def receive_json(self):
        return self.ws.receive_json()


def _clear_caches(*room_codes):
    from routers.game import boards_cache, turn_start_cache
    for rc in room_codes:
        boards_cache.pop(rc, None)
        turn_start_cache.pop(rc, None)


class TestWebSocketAuth:
    def test_ws_no_auth_message_closes(self, mock_db):
        """WS without auth message should be rejected."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        tc = TestClient(app)
        with tc.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.send_json({"type": "move", "from": "e2", "to": "e4"})
            resp = ws.receive_json()
            assert resp["type"] == "error"

    def test_ws_non_player_rejected(self, mock_db):
        """User who is not a player should be rejected."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        tc = TestClient(app)
        with tc.websocket_connect("/api/ws/game/ABC123") as ws:
            ws.send_json({"type": "auth", "user_id": 999})
            resp = ws.receive_json()
            assert resp["type"] == "error"
            assert "not a player" in resp["message"].lower()

    def test_ws_nonexistent_game(self, mock_db):
        """WS to non-existent game should close."""
        mock_db.read_one.return_value = None
        tc = TestClient(app)
        with tc.websocket_connect("/api/ws/game/NOPE00") as ws:
            ws.send_json({"type": "auth", "user_id": 1})
            resp = ws.receive_json()
            assert resp["type"] == "error"


class TestWebSocketGameplay:
    def _setup(self, mock_db):
        _clear_caches("ABC123")
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

    def _cleanup(self):
        _clear_caches("ABC123")

    def test_ws_init_message(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            assert s.init_data["type"] == "init"
            assert s.init_data["fen"] == INITIAL_FEN
            assert s.init_data["status"] == "active"
            assert s.init_data["your_side"] == "w"
            assert s.init_data["turn"] == "w"
            assert "players" in s.init_data
            assert "moves" in s.init_data
            assert s.init_data["moves"] == []
            assert "time_per_move" in s.init_data
            assert "turn_started_at" in s.init_data
        self._cleanup()

    def test_ws_init_includes_players(self, mock_db):
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            players = s.init_data["players"]
            assert players["white"]["name"] == "alice"
            assert players["black"]["name"] == "bob"
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
            assert update["last_move"]["color"] == "w"
            assert update["last_move"]["move_number"] == 1
            assert "turn_started_at" in update
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

    def test_ws_timeout_ignored_when_no_timer(self, mock_db):
        """Timeout message should be ignored when game has no time_per_move."""
        self._setup(mock_db)
        tc = TestClient(app)
        with WSSession(tc, "ABC123", 1, mock_db, FAKE_GAME_ACTIVE) as s:
            s.send_json({"type": "timeout"})
            # Should not crash; send a move to confirm connection still works
            s.send_json({"type": "move", "from": "e2", "to": "e4"})
            resp = s.receive_json()
            assert resp["type"] == "update"
        self._cleanup()


class TestWebSocketWithTimer:
    def _setup(self, mock_db):
        _clear_caches("TIMED1")
        mock_db.execute_returning.return_value = {
            **FAKE_GAME_ACTIVE, "room_code": "TIMED1", "time_per_move": 30,
        }

    def _cleanup(self):
        _clear_caches("TIMED1")

    def test_init_includes_time_per_move(self, mock_db):
        self._setup(mock_db)
        game = {**FAKE_GAME_ACTIVE, "room_code": "TIMED1", "time_per_move": 30}
        tc = TestClient(app)
        with WSSession(tc, "TIMED1", 1, mock_db, game) as s:
            assert s.init_data["time_per_move"] == 30
            assert s.init_data["turn_started_at"] is not None
        self._cleanup()

    def test_move_includes_time_per_move(self, mock_db):
        self._setup(mock_db)
        game = {**FAKE_GAME_ACTIVE, "room_code": "TIMED1", "time_per_move": 30}
        tc = TestClient(app)
        with WSSession(tc, "TIMED1", 1, mock_db, game) as s:
            s.send_json({"type": "move", "from": "e2", "to": "e4"})
            update = s.receive_json()
            assert update["time_per_move"] == 30
            assert update["turn_started_at"] is not None
        self._cleanup()


class TestBoardCacheIsolation:
    def test_separate_rooms(self, mock_db):
        game_a = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_A"}
        game_b = {**FAKE_GAME_ACTIVE, "room_code": "ROOM_B"}
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        _clear_caches("ROOM_A", "ROOM_B")

        tc = TestClient(app)
        with WSSession(tc, "ROOM_A", 1, mock_db, game_a) as sa:
            sa.send_json({"type": "move", "from": "e2", "to": "e4"})
            fen_a = sa.receive_json()["fen"]

        with WSSession(tc, "ROOM_B", 1, mock_db, game_b) as sb:
            sb.send_json({"type": "move", "from": "d2", "to": "d4"})
            fen_b = sb.receive_json()["fen"]

        assert fen_a != fen_b
        _clear_caches("ROOM_A", "ROOM_B")
