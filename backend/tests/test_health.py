"""Tests for root and health endpoints."""
import pytest
from tests.conftest import FAKE_USER_WHITE


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "Pawnly" in data["message"]


@pytest.mark.asyncio
async def test_health_ok(client, mock_db):
    mock_db.read_one.return_value = {"ok": 1}
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"


@pytest.mark.asyncio
async def test_health_db_fail(client, mock_db):
    mock_db.read_one.side_effect = Exception("connection refused")
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert "connection refused" in data["db"]
    mock_db.read_one.side_effect = None  # reset
