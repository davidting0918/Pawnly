"""Tests for game REST endpoints (create, join, get)."""
import pytest
from datetime import datetime
from copy import deepcopy

from tests.conftest import (
    FAKE_USER_WHITE,
    FAKE_USER_BLACK,
    FAKE_GAME_WAITING,
    FAKE_GAME_ACTIVE,
    INITIAL_FEN,
    make_token,
)


class TestCreateGame:
    @pytest.mark.asyncio
    async def test_create_game_white(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {
            "id": 10, "room_code": "ABC123", "status": "waiting", "time_per_move": None,
        }

        resp = await client.post("/api/games", json={"side": "white"}, headers=auth_headers_white)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting"
        assert data["side"] == "white"
        assert len(data["room_code"]) == 6
        assert data["time_per_move"] is None

    @pytest.mark.asyncio
    async def test_create_game_black(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {
            "id": 10, "room_code": "ABC123", "status": "waiting", "time_per_move": None,
        }

        resp = await client.post("/api/games", json={"side": "black"}, headers=auth_headers_white)
        assert resp.status_code == 200
        data = resp.json()
        assert data["side"] == "black"

    @pytest.mark.asyncio
    async def test_create_game_default_white(self, client, mock_db, auth_headers_white):
        """Default side should be white."""
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {
            "id": 10, "room_code": "ABC123", "status": "waiting", "time_per_move": None,
        }

        resp = await client.post("/api/games", json={}, headers=auth_headers_white)
        assert resp.status_code == 200
        assert resp.json()["side"] == "white"

    @pytest.mark.asyncio
    async def test_create_game_with_time_per_move(self, client, mock_db, auth_headers_white):
        """Creating a game with time_per_move should include it in the response."""
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {
            "id": 10, "room_code": "ABC123", "status": "waiting", "time_per_move": 30,
        }

        resp = await client.post(
            "/api/games",
            json={"side": "white", "time_per_move": 30},
            headers=auth_headers_white,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["time_per_move"] == 30

    @pytest.mark.asyncio
    async def test_create_game_invalid_side(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        resp = await client.post("/api/games", json={"side": "purple"}, headers=auth_headers_white)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_game_no_auth(self, client):
        resp = await client.post("/api/games", json={"side": "white"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_game_returns_id(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {
            "id": 42, "room_code": "ZZZ999", "status": "waiting", "time_per_move": None,
        }

        resp = await client.post("/api/games", json={"side": "white"}, headers=auth_headers_white)
        assert resp.json()["id"] == 42


class TestJoinGame:
    @pytest.mark.asyncio
    async def test_join_game_success(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [
            FAKE_USER_BLACK,      # auth
            FAKE_GAME_WAITING,    # get_game_by_room_code
        ]
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert "side" in data
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_nonexistent_game(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [FAKE_USER_BLACK, None]
        resp = await client.post("/api/games/NOPE00/join", headers=auth_headers_black)
        assert resp.status_code == 404
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_already_active_game(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [FAKE_USER_BLACK, FAKE_GAME_ACTIVE]
        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 400
        assert "not waiting" in resp.json()["detail"]
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_own_game_white(self, client, mock_db, auth_headers_white):
        mock_db.read_one.side_effect = [FAKE_USER_WHITE, FAKE_GAME_WAITING]
        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_white)
        assert resp.status_code == 400
        assert "own game" in resp.json()["detail"].lower()
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_game_no_auth(self, client):
        resp = await client.post("/api/games/ABC123/join")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_join_game_db_returns_none(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [FAKE_USER_BLACK, FAKE_GAME_WAITING]
        mock_db.execute_returning.return_value = None
        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 400
        assert "Failed to join" in resp.json()["detail"]
        mock_db.read_one.side_effect = None


class TestGetGame:
    @pytest.mark.asyncio
    async def test_get_game_as_player(self, client, mock_db, auth_headers_white):
        """Player in the game can view it."""
        mock_db.read_one.side_effect = [FAKE_USER_WHITE, FAKE_GAME_WAITING]
        resp = await client.get("/api/games/ABC123", headers=auth_headers_white)
        assert resp.status_code == 200
        data = resp.json()
        assert data["room_code"] == "ABC123"
        assert "time_per_move" in data
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_get_game_not_found(self, client, mock_db, auth_headers_white):
        mock_db.read_one.side_effect = [FAKE_USER_WHITE, None]
        resp = await client.get("/api/games/NOPE00", headers=auth_headers_white)
        assert resp.status_code == 404
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_get_game_blocked_for_non_player(self, client, mock_db, auth_headers_black):
        """User not in the game should get 403."""
        mock_db.read_one.side_effect = [FAKE_USER_BLACK, FAKE_GAME_WAITING]
        resp = await client.get("/api/games/ABC123", headers=auth_headers_black)
        assert resp.status_code == 403
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_get_game_requires_auth(self, client, mock_db):
        """GET game now requires auth."""
        resp = await client.get("/api/games/ABC123")
        assert resp.status_code == 401
