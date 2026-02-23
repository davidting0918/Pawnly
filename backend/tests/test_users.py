"""Tests for user endpoints (profile, game history, leaderboard)."""
import pytest
from datetime import datetime

from tests.conftest import (
    FAKE_USER_WHITE,
    FAKE_USER_BLACK,
    make_token,
)


class TestUserProfile:
    @pytest.mark.asyncio
    async def test_get_me(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        resp = await client.get("/api/users/me", headers=auth_headers_white)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["username"] == "alice@example.com"
        assert data["elo_rating"] == 1200

    @pytest.mark.asyncio
    async def test_get_me_no_auth(self, client):
        resp = await client.get("/api/users/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_has_created_at(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        resp = await client.get("/api/users/me", headers=auth_headers_white)
        data = resp.json()
        assert "created_at" in data


class TestUserGames:
    @pytest.mark.asyncio
    async def test_user_games_empty(self, client, mock_db):
        mock_db.read.return_value = []
        resp = await client.get("/api/users/1/games")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_user_games_with_data(self, client, mock_db):
        mock_db.read.return_value = [
            {
                "id": 10,
                "room_code": "ABC123",
                "status": "finished",
                "winner_id": 1,
                "created_at": datetime(2026, 2, 1),
                "updated_at": datetime(2026, 2, 1),
                "white_player_id": 1,
                "black_player_id": 2,
                "white_username": "alice@example.com",
                "white_elo": 1200,
                "black_username": "bob@example.com",
                "black_elo": 1300,
                "fen": "some_fen",
                "pgn": "",
            }
        ]
        resp = await client.get("/api/users/1/games")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "finished"
        assert data[0]["winner_id"] == 1
        assert data[0]["white_player"]["username"] == "alice@example.com"
        assert data[0]["black_player"]["username"] == "bob@example.com"

    @pytest.mark.asyncio
    async def test_user_games_limit_param(self, client, mock_db):
        mock_db.read.return_value = []
        resp = await client.get("/api/users/1/games?limit=5")
        assert resp.status_code == 200
        # Verify the limit was passed to DB query
        call_args = mock_db.read.call_args
        assert call_args[0][2] == 5  # third arg is limit

    @pytest.mark.asyncio
    async def test_user_games_no_auth_required(self, client, mock_db):
        """Game history should be public."""
        mock_db.read.return_value = []
        resp = await client.get("/api/users/1/games")
        assert resp.status_code == 200


class TestLeaderboard:
    @pytest.mark.asyncio
    async def test_leaderboard_empty(self, client, mock_db):
        mock_db.read.return_value = []
        resp = await client.get("/api/users/leaderboard")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_leaderboard_sorted(self, client, mock_db):
        mock_db.read.return_value = [
            {"id": 2, "username": "bob@example.com", "elo_rating": 1300, "created_at": datetime(2026, 1, 2)},
            {"id": 1, "username": "alice@example.com", "elo_rating": 1200, "created_at": datetime(2026, 1, 1)},
        ]
        resp = await client.get("/api/users/leaderboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["elo_rating"] >= data[1]["elo_rating"]

    @pytest.mark.asyncio
    async def test_leaderboard_limit(self, client, mock_db):
        mock_db.read.return_value = []
        resp = await client.get("/api/users/leaderboard?limit=3")
        assert resp.status_code == 200
        call_args = mock_db.read.call_args
        assert call_args[0][1] == 3
