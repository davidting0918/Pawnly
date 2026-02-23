"""Tests for service-layer logic (game_service, user_service)."""
import pytest
from datetime import datetime

from tests.conftest import FAKE_USER_WHITE, FAKE_GAME_WAITING


class TestGameServiceRoomCode:
    def test_room_code_length(self):
        from services.game_service import generate_room_code
        code = generate_room_code()
        assert len(code) == 6

    def test_room_code_custom_length(self):
        from services.game_service import generate_room_code
        code = generate_room_code(length=8)
        assert len(code) == 8

    def test_room_code_chars(self):
        from services.game_service import generate_room_code
        import string
        valid = set(string.ascii_uppercase + string.digits)
        for _ in range(50):
            code = generate_room_code()
            assert all(c in valid for c in code)

    def test_room_code_uniqueness(self):
        from services.game_service import generate_room_code
        codes = {generate_room_code() for _ in range(100)}
        # With 36^6 possibilities, 100 codes should all be unique
        assert len(codes) == 100


class TestGameServiceDB:
    @pytest.mark.asyncio
    async def test_create_game_calls_db(self, mock_db):
        mock_db.execute_returning.return_value = {
            "id": 1, "room_code": "ABC123", "status": "waiting",
            "white_player_id": 1, "black_player_id": None,
        }
        from services.game_service import create_game
        result = await create_game(user_id=1)
        assert result["status"] == "waiting"
        assert result["white_player_id"] == 1
        mock_db.execute_returning.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_game_calls_db(self, mock_db):
        mock_db.execute_returning.return_value = {
            "id": 1, "room_code": "ABC123", "status": "active",
            "white_player_id": 1, "black_player_id": 2,
        }
        from services.game_service import join_game
        result = await join_game(game_id=1, user_id=2)
        assert result["status"] == "active"
        assert result["black_player_id"] == 2

    @pytest.mark.asyncio
    async def test_get_game_by_room_code(self, mock_db):
        mock_db.read_one.return_value = FAKE_GAME_WAITING
        from services.game_service import get_game_by_room_code
        result = await get_game_by_room_code("ABC123")
        assert result["room_code"] == "ABC123"

    @pytest.mark.asyncio
    async def test_get_game_not_found(self, mock_db):
        mock_db.read_one.return_value = None
        from services.game_service import get_game_by_room_code
        result = await get_game_by_room_code("NOPE00")
        assert result is None

    @pytest.mark.asyncio
    async def test_record_move(self, mock_db):
        mock_db.execute_returning.return_value = {
            "id": 1, "game_id": 10, "move_number": 1,
            "color": "w", "san": "e4", "uci": "e2e4",
        }
        from services.game_service import record_move
        result = await record_move(10, 1, "w", "e4", "e2e4", "some_fen")
        assert result["san"] == "e4"
        mock_db.execute_returning.assert_called_once()

    @pytest.mark.asyncio
    async def test_abort_game(self, mock_db):
        mock_db.execute_returning.return_value = {**FAKE_GAME_WAITING, "status": "aborted"}
        from services.game_service import abort_game
        result = await abort_game(10)
        assert result["status"] == "aborted"


class TestUserServiceDB:
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_db):
        mock_db.read_one.return_value = FAKE_USER_WHITE
        from services.user_service import get_user_by_id
        result = await get_user_by_id(1)
        assert result["username"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, mock_db):
        mock_db.read_one.return_value = None
        from services.user_service import get_user_by_id
        result = await get_user_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_user(self, mock_db):
        mock_db.execute_returning.return_value = {
            "id": 3, "username": "new@example.com",
            "hashed_password": "hash", "elo_rating": 1200,
            "created_at": datetime(2026, 2, 23),
        }
        from services.user_service import create_user
        result = await create_user("new@example.com", "hash")
        assert result["id"] == 3

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, mock_db):
        mock_db.read.return_value = [
            {"id": 2, "username": "bob", "elo_rating": 1500, "created_at": datetime(2026, 1, 1)},
            {"id": 1, "username": "alice", "elo_rating": 1200, "created_at": datetime(2026, 1, 1)},
        ]
        from services.user_service import get_leaderboard
        result = await get_leaderboard(10)
        assert len(result) == 2
        assert result[0]["elo_rating"] > result[1]["elo_rating"]

    @pytest.mark.asyncio
    async def test_update_elo(self, mock_db):
        from services.user_service import update_elo
        await update_elo(1, 1350)
        mock_db.execute.assert_called_once()
        args = mock_db.execute.call_args[0]
        assert 1350 in args
        assert 1 in args
