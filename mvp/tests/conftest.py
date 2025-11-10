"""Pytest configuration and fixtures."""

import os

import pytest
import pytest_asyncio

from eidolon_mvp.memory import MemoryStore


@pytest.fixture(scope="session")
def db_url():
    """Get test database URL."""
    return os.getenv("TEST_DATABASE_URL", "postgresql://localhost/eidolon_mvp_test")


@pytest_asyncio.fixture
async def memory_store(db_url):
    """Create a memory store for testing."""
    store = MemoryStore(db_url)
    await store.connect()
    yield store
    await store.close()


@pytest.fixture
def sample_commit_sha():
    """Sample commit SHA for testing."""
    return "abc123def456"
