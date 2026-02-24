"""Tests for bot game functionality."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.conftest import (
    FAKE_USER_WHITE,
    FAKE_GAME_WAITING,
    INITIAL_FEN,
    make_token,
    _mock_db,
)

# ── Fake bot game data ──

FAKE_BOT_GAME = {
    "id": 20,
    "room_code": "BOT001",
    "white_player_id": 1,
    "black_player_id": None,
    "fen": INITIAL_FEN,
    "pgn": "",
    "status": "active",
    "winner_id": None,
    "time_per_move": None,
    "is_bot_game": True,
    "bot_difficulty": "medium",
    "created_at": datetime(2026, 2, 1),
    "updated_at": datetime(2026, 2, 1),
}

FAKE_BOT_GAME_BLACK = {
    **FAKE_BOT_GAME,
    "id": 21,
    "room_code": "BOT002",
    "white_player_id": None,
    "black_player_id": 1,
}


# ── REST endpoint tests ──


class TestCreateBotGame:
    """POST /api/games/bot"""

    @pytest.mark.anyio
    async def test_create_bot_game_success(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = FAKE_BOT_GAME

        res = await client.post(
            "/api/games/bot",
            json={"side": "white", "difficulty": "medium"},
            headers=auth_headers_white,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_bot_game"] is True
        assert data["difficulty"] == "medium"
        assert data["status"] == "active"

    @pytest.mark.anyio
    async def test_create_bot_game_all_difficulties(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        for diff in ["beginner", "easy", "medium", "hard", "expert"]:
            mock_db.execute_returning.return_value = {**FAKE_BOT_GAME, "bot_difficulty": diff}
            res = await client.post(
                "/api/games/bot",
                json={"side": "white", "difficulty": diff},
                headers=auth_headers_white,
            )
            assert res.status_code == 200
            assert res.json()["difficulty"] == diff

    @pytest.mark.anyio
    async def test_create_bot_game_invalid_difficulty(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        res = await client.post(
            "/api/games/bot",
            json={"side": "white", "difficulty": "impossible"},
            headers=auth_headers_white,
        )
        assert res.status_code == 400
        assert "difficulty" in res.json()["detail"]

    @pytest.mark.anyio
    async def test_create_bot_game_invalid_side(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        res = await client.post(
            "/api/games/bot",
            json={"side": "random", "difficulty": "medium"},
            headers=auth_headers_white,
        )
        assert res.status_code == 400

    @pytest.mark.anyio
    async def test_create_bot_game_as_black(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = FAKE_BOT_GAME_BLACK

        res = await client.post(
            "/api/games/bot",
            json={"side": "black", "difficulty": "hard"},
            headers=auth_headers_white,
        )
        assert res.status_code == 200
        assert res.json()["side"] == "black"

    @pytest.mark.anyio
    async def test_create_bot_game_with_timer(self, client, mock_db, auth_headers_white):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {**FAKE_BOT_GAME, "time_per_move": 30}

        res = await client.post(
            "/api/games/bot",
            json={"side": "white", "difficulty": "easy", "time_per_move": 30},
            headers=auth_headers_white,
        )
        assert res.status_code == 200
        assert res.json()["time_per_move"] == 30

    @pytest.mark.anyio
    async def test_create_bot_game_no_auth(self, client, mock_db):
        res = await client.post(
            "/api/games/bot",
            json={"side": "white", "difficulty": "medium"},
        )
        assert res.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_create_bot_game_defaults(self, client, mock_db, auth_headers_white):
        """Default side=white, difficulty=medium."""
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = FAKE_BOT_GAME

        res = await client.post(
            "/api/games/bot",
            json={},
            headers=auth_headers_white,
        )
        assert res.status_code == 200


# ── Bot service unit tests ──


class TestBotService:
    """Unit tests for services/bot_service.py."""

    def test_difficulty_config(self):
        from services.bot_service import get_difficulty_config, VALID_DIFFICULTIES

        for diff in VALID_DIFFICULTIES:
            config = get_difficulty_config(diff)
            assert "skill" in config
            assert "time" in config
            assert "elo" in config
            assert 0 <= config["skill"] <= 20

    def test_invalid_difficulty_returns_medium(self):
        from services.bot_service import get_difficulty_config

        config = get_difficulty_config("nonexistent")
        assert config == get_difficulty_config("medium")

    def test_bot_elo(self):
        from services.bot_service import get_bot_elo

        assert get_bot_elo("beginner") == 800
        assert get_bot_elo("expert") == 2500

    def test_bot_display_name(self):
        from services.bot_service import get_bot_display_name

        name = get_bot_display_name("hard")
        assert "Bot" in name
        assert "Hard" in name


# ── Elo calculation tests for bot games ──


class TestBotElo:
    """Test that bot Elo updates use bot_elo field, not regular elo."""

    def test_elo_calculation_is_reused(self):
        from services.game_service import calculate_elo

        # Human (1200) beats bot (800) → should gain less Elo
        new_h, new_b = calculate_elo(1200, 800, "white")
        assert new_h > 1200
        assert new_h - 1200 < 16  # Small gain vs weak opponent

        # Human (1200) beats bot (2500) → should gain a lot
        new_h2, _ = calculate_elo(1200, 2500, "white")
        assert new_h2 - 1200 > 25  # Big gain vs strong opponent


# ── Game players display for bot games ──


class TestBotPlayerDisplay:

    @pytest.mark.anyio
    async def test_get_game_players_bot_white_human(self, mock_db):
        """Human plays white, bot plays black."""
        mock_db.read_one.return_value = {"id": 1, "username": "alice@example.com"}

        from services.game_service import get_game_players_bot

        players = await get_game_players_bot(FAKE_BOT_GAME)
        assert players["white"]["name"] == "alice"
        assert players["black"]["id"] == -1
        assert "Bot" in players["black"]["name"]

    @pytest.mark.anyio
    async def test_get_game_players_bot_black_human(self, mock_db):
        """Human plays black, bot plays white."""
        mock_db.read_one.return_value = {"id": 1, "username": "alice@example.com"}

        from services.game_service import get_game_players_bot

        players = await get_game_players_bot(FAKE_BOT_GAME_BLACK)
        assert players["white"]["id"] == -1
        assert "Bot" in players["white"]["name"]
        assert players["black"]["name"] == "alice"


# ── Leaderboard tests ──


class TestBotLeaderboard:

    @pytest.mark.anyio
    async def test_leaderboard_default_is_human(self, client, mock_db):
        mock_db.read.return_value = [
            {"id": 1, "username": "alice", "elo_rating": 1400, "bot_elo": 1200, "created_at": datetime(2026, 1, 1)}
        ]
        res = await client.get("/api/users/leaderboard")
        assert res.status_code == 200
        assert len(res.json()) == 1

    @pytest.mark.anyio
    async def test_leaderboard_bot_type(self, client, mock_db):
        mock_db.read.return_value = [
            {"id": 1, "username": "alice", "elo_rating": 1200, "bot_elo": 1500, "created_at": datetime(2026, 1, 1)}
        ]
        res = await client.get("/api/users/leaderboard?type=bot")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["bot_elo"] == 1500


# ── Profile includes bot_elo ──


class TestProfileBotElo:

    @pytest.mark.anyio
    async def test_profile_includes_bot_elo(self, client, mock_db, auth_headers_white):
        user_with_bot_elo = {**FAKE_USER_WHITE, "bot_elo": 1350}
        mock_db.read_one.return_value = user_with_bot_elo
        res = await client.get("/api/users/me", headers=auth_headers_white)
        assert res.status_code == 200
        data = res.json()
        assert data["bot_elo"] == 1350
        assert data["elo_rating"] == 1200


# ── Game history filter ──


class TestGameHistoryFilter:

    @pytest.mark.anyio
    async def test_games_filter_bot(self, client, mock_db):
        mock_db.read.return_value = [
            {
                **FAKE_BOT_GAME,
                "white_username": "alice",
                "white_elo": 1200,
                "black_username": None,
                "black_elo": None,
            },
            {
                **FAKE_GAME_WAITING,
                "status": "finished",
                "is_bot_game": False,
                "bot_difficulty": None,
                "white_username": "alice",
                "white_elo": 1200,
                "black_username": "bob",
                "black_elo": 1300,
                "black_player_id": 2,
            },
        ]

        # Filter bot only
        res = await client.get("/api/users/1/games?type=bot")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["is_bot_game"] is True

    @pytest.mark.anyio
    async def test_games_filter_human(self, client, mock_db):
        mock_db.read.return_value = [
            {
                **FAKE_BOT_GAME,
                "white_username": "alice",
                "white_elo": 1200,
                "black_username": None,
                "black_elo": None,
            },
            {
                **FAKE_GAME_WAITING,
                "status": "finished",
                "is_bot_game": False,
                "bot_difficulty": None,
                "white_username": "alice",
                "white_elo": 1200,
                "black_username": "bob",
                "black_elo": 1300,
                "black_player_id": 2,
            },
        ]

        res = await client.get("/api/users/1/games?type=human")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["is_bot_game"] is False
