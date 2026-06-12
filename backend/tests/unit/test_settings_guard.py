"""JWT secret / environment guard (P1 hardening)."""
import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_production_refuses_default_secret():
    s = _settings(ENVIRONMENT="production", JWT_SECRET="changeme-jwt-secret")
    with pytest.raises(RuntimeError):
        s.validate_runtime()


def test_production_refuses_short_secret():
    s = _settings(ENVIRONMENT="production", JWT_SECRET="short")
    with pytest.raises(RuntimeError):
        s.validate_runtime()


def test_production_accepts_strong_secret():
    s = _settings(ENVIRONMENT="production", JWT_SECRET="x" * 64)
    s.validate_runtime()


def test_development_tolerates_default_secret():
    s = _settings(ENVIRONMENT="development", JWT_SECRET="changeme-secret")
    s.validate_runtime()


def test_cors_origins():
    assert _settings(ENVIRONMENT="development").cors_origins_list == ["*"]
    assert _settings(ENVIRONMENT="production", JWT_SECRET="x" * 64).cors_origins_list == []
    s = _settings(CORS_ORIGINS="https://vpn.example.com, https://admin.example.com")
    assert s.cors_origins_list == ["https://vpn.example.com", "https://admin.example.com"]
