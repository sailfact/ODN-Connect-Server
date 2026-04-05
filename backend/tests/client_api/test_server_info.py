"""
ODN Connect contract tests for /api/client/server-info.
These guard against breaking changes that would break the desktop client.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_server_info_shape():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/client/server-info")
    assert r.status_code == 200
    data = r.json()
    required_keys = {"server_name", "public_key", "endpoint", "dns", "allowed_ips", "api_base_url"}
    assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"
    assert isinstance(data["dns"], list)
    assert ":" in data["endpoint"]  # host:port format


@pytest.mark.asyncio
async def test_server_info_no_auth_required():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/client/server-info")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_server_info_no_sensitive_fields():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/client/server-info")
    data = r.json()
    forbidden = {"private_key", "peers", "password", "secret"}
    assert not forbidden.intersection(data.keys())
