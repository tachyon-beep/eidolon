import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from eidolon.cache.cache_manager import CacheManager


@pytest_asyncio.fixture()
async def cache(tmp_path):
    db_path = tmp_path / "cache.db"
    mgr = CacheManager(db_path=str(db_path))
    await mgr.initialize()
    return mgr


def write_file(path: Path, content: str):
    path.write_text(content)


@pytest.mark.asyncio
async def test_store_and_get_cached_result(cache: CacheManager, tmp_path):
    file_path = tmp_path / "sample.py"
    write_file(file_path, "def foo():\n    return 1\n")

    key = await cache.store_result(
        file_path=str(file_path),
        scope="Function",
        target="foo",
        findings=["ok"],
        cards_data=[{"id": "c1"}],
        metrics={"complexity": 1},
    )
    assert key

    entry = await cache.get_cached_result(
        file_path=str(file_path),
        scope="Function",
        target="foo",
    )
    assert entry
    assert entry.findings == ["ok"]
    assert cache.session_hits == 1
    assert cache.session_misses == 0


@pytest.mark.asyncio
async def test_cache_miss_on_changed_file(cache: CacheManager, tmp_path):
    file_path = tmp_path / "sample.py"
    write_file(file_path, "def foo():\n    return 1\n")

    await cache.store_result(
        file_path=str(file_path),
        scope="Function",
        target="foo",
        findings=[],
        cards_data=[],
        metrics={},
    )

    write_file(file_path, "def foo():\n    return 2\n")
    entry = await cache.get_cached_result(
        file_path=str(file_path),
        scope="Function",
        target="foo",
    )
    assert entry is None
    assert cache.session_misses >= 1


@pytest.mark.asyncio
async def test_invalidate_and_stats(cache: CacheManager, tmp_path):
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    write_file(file_a, "a=1\n")
    write_file(file_b, "b=2\n")

    await cache.store_result(str(file_a), "Module", "module", [], [], {})
    await cache.store_result(str(file_b), "Module", "module", [], [], {})
    await cache.get_cached_result(str(file_a), "Module", "module")

    deleted = await cache.invalidate_file(str(file_b))
    assert deleted == 1

    stats = await cache.get_statistics()
    assert stats.total_entries == 1
    assert stats.hits >= 1
    assert stats.misses >= 0
    assert stats.most_accessed_file == str(file_a)


@pytest.mark.asyncio
async def test_prune_and_clear(cache: CacheManager, tmp_path, monkeypatch):
    file_path = tmp_path / "old.py"
    write_file(file_path, "x=1\n")

    await cache.store_result(str(file_path), "Module", "module", [], [], {})
    stats_before = await cache.get_statistics()
    assert stats_before.total_entries == 1

    # Force last_accessed to be old
    import aiosqlite

    async with aiosqlite.connect(cache.db_path) as db:
        await db.execute("UPDATE analysis_cache SET last_accessed = ?", (0,))
        await db.commit()

    pruned = await cache.prune_old_entries(max_age_days=1)
    assert pruned == 1

    remaining = await cache.clear_all()
    assert remaining == 0
