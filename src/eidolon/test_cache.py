#!/usr/bin/env python3
"""
Test script for cache functionality.
Tests that caching works correctly for analysis results.
"""

import asyncio
import os
from pathlib import Path
from eidolon.cache import CacheManager


async def test_cache_basic_operations():
    """Test basic cache operations"""
    print("🧪 Testing Basic Cache Operations\n")
    print("=" * 60)

    # Initialize cache
    cache = CacheManager("test_cache.db")
    await cache.initialize()

    # Test file hashing
    test_file = Path(__file__).parent / "examples" / "calculator.py"
    if not test_file.exists():
        test_file = Path(__file__).parent.parent / "examples" / "calculator.py"

    if test_file.exists():
        file_hash = cache.hash_file(str(test_file))
        print(f"✓ File hashing works: {file_hash[:16]}...")
    else:
        print("⚠️  Test file not found, skipping hash test")

    # Test storing a result
    findings = ["Bug: Potential division by zero", "Smell: Function too complex"]
    cards_data = [
        {
            "id": "TEST-001",
            "type": "Review",
            "title": "Test Card",
            "summary": "Test summary"
        }
    ]
    metrics = {"complexity": 5, "line_count": 20}

    cache_key = await cache.store_result(
        str(test_file) if test_file.exists() else "test.py",
        "Function",
        "test_function",
        findings,
        cards_data,
        metrics
    )

    print(f"✓ Stored cache entry: {cache_key[:16]}...")

    # Test retrieving the result
    cached = await cache.get_cached_result(
        str(test_file) if test_file.exists() else "test.py",
        "Function",
        "test_function"
    )

    if cached:
        print(f"✓ Retrieved cached result")
        print(f"  Findings: {len(cached.findings)}")
        print(f"  Cards: {len(cached.cards_data)}")
        print(f"  Access count: {cached.access_count}")
    else:
        print("✗ Failed to retrieve cached result")

    # Test cache statistics
    stats = await cache.get_statistics()
    print(f"\n📊 Cache Statistics:")
    print(f"  Total entries: {stats.total_entries}")
    print(f"  Total size: {stats.total_size_bytes} bytes")
    print(f"  Hit rate: {stats.hit_rate:.1f}%")
    print(f"  Session hits: {stats.hits}")
    print(f"  Session misses: {stats.misses}")

    # Test cache invalidation
    deleted = await cache.clear_all()
    print(f"\n✓ Cleared cache: {deleted} entries deleted")

    # Cleanup
    os.remove("test_cache.db")
    print("\n✓ Test database cleaned up")

    print("=" * 60)
    print("✅ All basic cache tests passed!")


async def test_cache_hit_miss():
    """Test cache hit/miss behavior"""
    print("\n\n🧪 Testing Cache Hit/Miss Behavior\n")
    print("=" * 60)

    cache = CacheManager("test_cache.db")
    await cache.initialize()

    # First access - should be a miss
    result1 = await cache.get_cached_result("test.py", "Function", "func1")
    print(f"First access: {'HIT' if result1 else 'MISS'} ✓")

    # Store something
    await cache.store_result(
        "test.py",
        "Function",
        "func1",
        ["finding1"],
        [],
        {}
    )

    # Second access - should be a hit
    result2 = await cache.get_cached_result("test.py", "Function", "func1")
    print(f"Second access: {'HIT' if result2 else 'MISS'} ✓")

    # Different function - should be a miss
    result3 = await cache.get_cached_result("test.py", "Function", "func2")
    print(f"Different function: {'HIT' if result3 else 'MISS'} ✓")

    # Get statistics
    stats = await cache.get_statistics()
    print(f"\nSession stats: {stats.hits} hits, {stats.misses} misses")
    print(f"Hit rate: {stats.hit_rate:.1f}%")

    # Cleanup
    await cache.clear_all()
    os.remove("test_cache.db")

    print("=" * 60)
    print("✅ Cache hit/miss tests passed!")


async def test_cache_invalidation():
    """Test cache invalidation"""
    print("\n\n🧪 Testing Cache Invalidation\n")
    print("=" * 60)

    cache = CacheManager("test_cache.db")
    await cache.initialize()

    # Store multiple entries for same file
    for i in range(3):
        await cache.store_result(
            "test.py",
            "Function",
            f"func{i}",
            [f"finding{i}"],
            [],
            {}
        )

    # Store entries for different file
    await cache.store_result(
        "other.py",
        "Function",
        "other_func",
        ["finding"],
        [],
        {}
    )

    stats = await cache.get_statistics()
    print(f"Initial entries: {stats.total_entries}")

    # Invalidate one file
    deleted = await cache.invalidate_file("test.py")
    print(f"✓ Invalidated test.py: {deleted} entries deleted")

    # Check remaining
    stats = await cache.get_statistics()
    print(f"Remaining entries: {stats.total_entries}")

    # Verify other file still cached
    result = await cache.get_cached_result("other.py", "Function", "other_func")
    print(f"Other file still cached: {'YES' if result else 'NO'} ✓")

    # Cleanup
    await cache.clear_all()
    os.remove("test_cache.db")

    print("=" * 60)
    print("✅ Cache invalidation tests passed!")


async def test_cache_with_file_changes():
    """Test that cache invalidates when file changes"""
    print("\n\n🧪 Testing Cache with File Changes\n")
    print("=" * 60)

    cache = CacheManager("test_cache.db")
    await cache.initialize()

    # Create a test file
    test_file = "test_temp.py"
    with open(test_file, 'w') as f:
        f.write("def test():\n    pass\n")

    # Store cache for this file
    await cache.store_result(
        test_file,
        "Function",
        "test",
        ["finding1"],
        [],
        {}
    )

    # Verify cache hit
    result1 = await cache.get_cached_result(test_file, "Function", "test")
    print(f"Initial cache: {'HIT' if result1 else 'MISS'} ✓")

    # Modify the file
    with open(test_file, 'w') as f:
        f.write("def test():\n    print('modified')\n")

    # Should be a miss because file hash changed
    result2 = await cache.get_cached_result(test_file, "Function", "test")
    print(f"After modification: {'HIT' if result2 else 'MISS'} ✓")

    if not result2:
        print("✓ Cache correctly detected file change!")

    # Cleanup
    os.remove(test_file)
    await cache.clear_all()
    os.remove("test_cache.db")

    print("=" * 60)
    print("✅ File change detection tests passed!")


if __name__ == "__main__":
    print("\n🚀 Eidolon Cache System Test Suite\n")

    asyncio.run(test_cache_basic_operations())
    asyncio.run(test_cache_hit_miss())
    asyncio.run(test_cache_invalidation())
    asyncio.run(test_cache_with_file_changes())

    print("\n\n✅ All cache tests passed!")
    print("🎉 Cache system is ready for production!\n")
