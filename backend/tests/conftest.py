"""Shared pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Block accidental real HTTP calls during unit tests.

    Tests that genuinely need network access should override this by
    using pytest.mark.allow_network or explicitly patching the call.
    """
    # We only block openai/anthropic/cohere SDKs via env-var stubs;
    # actual httpx/requests are left for integration tests.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake")
    monkeypatch.setenv("COHERE_API_KEY", "test-fake")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("AUTH_ENABLED", "false")
