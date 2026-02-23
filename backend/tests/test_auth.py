"""Tests for authentication (JWT, token validation, Google OAuth flow)."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from jose import jwt

from tests.conftest import (
    FAKE_USER_WHITE,
    FAKE_USER_BLACK,
    make_token,
)


# ── JWT Token Tests ──

class TestJWT:
    def test_create_valid_token(self):
        token = make_token(FAKE_USER_WHITE)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_correct_claims(self):
        token = make_token(FAKE_USER_WHITE)
        payload = jwt.decode(token, "test_secret_key_for_testing", algorithms=["HS256"])
        assert payload["sub"] == "1"
        assert payload["username"] == "alice@example.com"
        assert "exp" in payload

    def test_token_expiration(self):
        token = make_token(FAKE_USER_WHITE)
        payload = jwt.decode(token, "test_secret_key_for_testing", algorithms=["HS256"])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        # Should expire within ~30 minutes (with some tolerance)
        now = datetime.now(timezone.utc)
        assert exp > now
        assert exp < now + timedelta(minutes=35)


# ── Protected Endpoint Access Tests ──

class TestProtectedAccess:
    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client):
        resp = await client.post("/api/games")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        resp = await client.post("/api/games", headers={"Authorization": "Bearer garbage_token"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client, mock_db):
        from core.security import create_access_token
        token = create_access_token(
            data={"sub": "1", "username": "alice@example.com"},
            expires_delta=timedelta(seconds=-10),  # already expired
        )
        resp = await client.post("/api/games", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_no_sub_returns_401(self, client, mock_db):
        """Token without 'sub' claim should be rejected."""
        from core.security import create_access_token
        token = create_access_token(data={"username": "alice@example.com"})
        resp = await client.post("/api/games", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_nonexistent_user_returns_401(self, client, mock_db):
        """Valid token but user not in DB."""
        mock_db.read_one.return_value = None  # user not found
        resp = await client.post("/api/games", headers={"Authorization": f"Bearer {make_token(FAKE_USER_WHITE)}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_with_existing_user_passes(self, client, mock_db):
        """Valid token + user in DB should pass auth."""
        mock_db.read_one.return_value = FAKE_USER_WHITE
        mock_db.execute_returning.return_value = {"id": 10, "room_code": "XYZ789", "status": "waiting", "time_per_move": None}
        resp = await client.post(
            "/api/games",
            json={"side": "white"},
            headers={"Authorization": f"Bearer {make_token(FAKE_USER_WHITE)}"},
        )
        assert resp.status_code == 200


# ── Google OAuth Endpoint Tests ──

class TestGoogleOAuth:
    @pytest.mark.asyncio
    async def test_google_login_invalid_token(self, client, mock_db):
        """Invalid Google credential should return 401."""
        resp = await client.post("/api/auth/google", json={"credential": "fake_token"})
        # Should be 401 (invalid token) or 500 depending on google-auth behavior
        assert resp.status_code in [401, 500]

    @pytest.mark.asyncio
    async def test_google_login_missing_credential(self, client):
        """Missing credential field should return 422."""
        resp = await client.post("/api/auth/google", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @patch("routers.auth.id_token.verify_oauth2_token")
    async def test_google_login_new_user(self, mock_verify, client, mock_db):
        """Successful Google login creates new user and returns token."""
        mock_verify.return_value = {"email": "newuser@example.com"}
        # get_user_by_username → read_one returns None (not found)
        mock_db.read_one.return_value = None
        # create_user → execute_returning returns new user
        mock_db.execute_returning.return_value = {
            "id": 99, "username": "newuser@example.com", "hashed_password": "google_auth_user",
            "elo_rating": 1200, "created_at": datetime(2026, 2, 23),
        }

        resp = await client.post("/api/auth/google", json={"credential": "valid_google_token"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "newuser@example.com"
        assert data["user_id"] == 99
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    @patch("routers.auth.id_token.verify_oauth2_token")
    async def test_google_login_existing_user(self, mock_verify, client, mock_db):
        """Existing user logs in without creating a new account."""
        mock_verify.return_value = {"email": "alice@example.com"}
        mock_db.read_one.return_value = FAKE_USER_WHITE  # user found

        resp = await client.post("/api/auth/google", json={"credential": "valid_google_token"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == FAKE_USER_WHITE["id"]
        assert data["username"] == "alice@example.com"
        # Should NOT have called execute_returning (no user creation)
        mock_db.execute_returning.assert_not_called()
