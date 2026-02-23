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
    async def test_create_game_success(self, client, mock_db, auth_headers_white):
        # Auth uses read_one, create_game uses execute_returning
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {"id": 10, "room_code": "ABC123", "status": "waiting"}

        resp = await client.post("/api/games", headers=auth_headers_white)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting"
        assert "room_code" in data
        assert len(data["room_code"]) == 6

    @pytest.mark.asyncio
    async def test_create_game_no_auth(self, client):
        resp = await client.post("/api/games")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_game_returns_id(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {"id": 42, "room_code": "ZZZ999", "status": "waiting"}

        resp = await client.post("/api/games", headers=auth_headers_white)
        data = resp.json()
        assert data["id"] == 42


class TestJoinGame:
    @pytest.mark.asyncio
    async def test_join_game_success(self, client, mock_db, auth_headers_black):
        # Auth: read_one → user; get_game_by_room_code: read_one → game
        mock_db.read_one.side_effect = [
            FAKE_USER_BLACK,      # auth
            FAKE_GAME_WAITING,    # get_game_by_room_code
        ]
        # join_game: execute_returning → updated game
        mock_db.execute_returning.return_value = FAKE_GAME_ACTIVE

        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_nonexistent_game(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [
            FAKE_USER_BLACK,  # auth
            None,             # game not found
        ]
        resp = await client.post("/api/games/NOPE00/join", headers=auth_headers_black)
        assert resp.status_code == 404
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_already_active_game(self, client, mock_db, auth_headers_black):
        mock_db.read_one.side_effect = [
            FAKE_USER_BLACK,   # auth
            FAKE_GAME_ACTIVE,  # game already active
        ]
        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 400
        assert "not waiting" in resp.json()["detail"]
        mock_db.read_one.side_effect = None

    @pytest.mark.asyncio
    async def test_join_own_game(self, client, mock_db, auth_headers_white):
        """White player (creator) tries to join their own game as black."""
        mock_db.read_one.side_effect = [
            FAKE_USER_WHITE,    # auth — user id=1
            FAKE_GAME_WAITING,  # game.white_player_id=1
        ]
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
        """join_game service returns None (race condition, already joined, etc.)."""
        mock_db.read_one.side_effect = [
            FAKE_USER_BLACK,    # auth
            FAKE_GAME_WAITING,  # game found
        ]
        # join_game execute_returning returns None
        mock_db.execute_returning.return_value = None
        resp = await client.post("/api/games/ABC123/join", headers=auth_headers_black)
        assert resp.status_code == 400
        assert "Failed to join" in resp.json()["detail"]
        mock_db.read_one.side_effect = None


class TestGetGame:
    @pytest.mark.asyncio
    async def test_get_game_success(self, client, mock_db):
        mock_db.read_one.return_value = FAKE_GAME_WAITING
        resp = await client.get("/api/games/ABC123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["room_code"] == "ABC123"
        assert data["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_get_game_not_found(self, client, mock_db):
        mock_db.read_one.return_value = None
        resp = await client.get("/api/games/NOPE00")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_game_no_auth_required(self, client, mock_db):
        """GET game state should work without authentication."""
        mock_db.read_one.return_value = FAKE_GAME_ACTIVE
        resp = await client.get("/api/games/ABC123")
        assert resp.status_code == 200
