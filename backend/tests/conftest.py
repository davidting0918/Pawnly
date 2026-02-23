"""
Shared fixtures for Pawnly backend tests.

Uses mock DB layer so tests run without a real PostgreSQL connection.
"""
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Patch db_client before importing app ──
# We replace the singleton with a mock so no real DB is needed.

_mock_db = AsyncMock()
_mock_db.init_pool = AsyncMock()
_mock_db.close = AsyncMock()
_mock_db.read = AsyncMock(return_value=[])
_mock_db.read_one = AsyncMock(return_value=None)
_mock_db.execute = AsyncMock(return_value="OK")
_mock_db.execute_returning = AsyncMock(return_value=None)

# Patch before main imports db_client
with patch.dict(os.environ, {
    "SECRET_KEY": "test_secret_key_for_testing",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "GOOGLE_CLIENT_ID": "test_google_client_id",
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "FRONTEND_URL": "http://localhost:5173",
}):
    import core.database
    core.database.db_client = _mock_db

    from main import app
    from core.security import create_access_token


# ── Helper: fake users ──
FAKE_USER_WHITE = {
    "id": 1,
    "username": "alice@example.com",
    "hashed_password": "google_auth_user",
    "elo_rating": 1200,
    "created_at": datetime(2026, 1, 1, 0, 0, 0),
}

FAKE_USER_BLACK = {
    "id": 2,
    "username": "bob@example.com",
    "hashed_password": "google_auth_user",
    "elo_rating": 1300,
    "created_at": datetime(2026, 1, 2, 0, 0, 0),
}

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

FAKE_GAME_WAITING = {
    "id": 10,
    "room_code": "ABC123",
    "white_player_id": 1,
    "black_player_id": None,
    "fen": INITIAL_FEN,
    "pgn": "",
    "status": "waiting",
    "winner_id": None,
    "created_at": datetime(2026, 2, 1),
    "updated_at": datetime(2026, 2, 1),
}

FAKE_GAME_ACTIVE = {
    **FAKE_GAME_WAITING,
    "black_player_id": 2,
    "status": "active",
}


def make_token(user: dict) -> str:
    """Create a valid JWT for a fake user."""
    return create_access_token(data={"sub": str(user["id"]), "username": user["username"]})


@pytest.fixture
def mock_db():
    """Reset mock DB between tests and return it."""
    _mock_db.reset_mock()
    _mock_db.read.return_value = []
    _mock_db.read_one.return_value = None
    _mock_db.execute.return_value = "OK"
    _mock_db.execute_returning.return_value = None
    return _mock_db


@pytest.fixture
def token_white():
    return make_token(FAKE_USER_WHITE)


@pytest.fixture
def token_black():
    return make_token(FAKE_USER_BLACK)


@pytest.fixture
def auth_headers_white(token_white):
    return {"Authorization": f"Bearer {token_white}"}


@pytest.fixture
def auth_headers_black(token_black):
    return {"Authorization": f"Bearer {token_black}"}


@pytest.fixture
async def client():
    """Async test client using httpx."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
