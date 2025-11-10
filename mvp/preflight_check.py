#!/usr/bin/env python3
"""Pre-flight check to verify system is ready."""

import asyncio
import os
import sys


async def main():
    """Run pre-flight checks."""
    print("Eidolon MVP - Pre-flight Check")
    print("=" * 60)
    print()

    checks_passed = 0
    checks_failed = 0

    # Check 1: Python imports
    print("1. Checking Python imports...")
    try:
        from src.eidolon_mvp.agents import FunctionAgent, ModuleAgent
        from src.eidolon_mvp.memory import MemoryStore
        from src.eidolon_mvp.llm.config import create_llm_from_env

        print("   ✓ All modules import successfully")
        checks_passed += 1
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        checks_failed += 1

    # Check 2: Database connection
    print("2. Checking database...")
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/eidolon_mvp")
    print(f"   URL: {db_url}")

    try:
        from src.eidolon_mvp.memory import MemoryStore

        store = MemoryStore(db_url)
        await store.connect()
        print("   ✓ Database connection successful")
        await store.close()
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        print("   Run: createdb eidolon_mvp && psql eidolon_mvp < SCHEMA.sql")
        checks_failed += 1

    # Check 3: LLM configuration
    print("3. Checking LLM configuration...")
    try:
        from src.eidolon_mvp.llm.config import create_llm_from_env

        llm = create_llm_from_env()
        if llm:
            print(f"   ✓ LLM configured")
            print(f"     Provider: {llm.provider}")
            print(f"     Model: {llm.model}")
            if llm.base_url:
                print(f"     Base URL: {llm.base_url}")
            checks_passed += 1
        else:
            print("   ⚠ No LLM configured (optional)")
            print("     Set LLM_PROVIDER and API key in .env for enhanced analysis")
            checks_passed += 1
    except Exception as e:
        print(f"   ✗ LLM check failed: {e}")
        checks_failed += 1

    # Check 4: Test data models
    print("4. Checking data models...")
    try:
        from src.eidolon_mvp.agents.models import Finding, Analysis
        from datetime import datetime

        finding = Finding(
            location="test.py:1",
            severity="high",
            type="bug",
            description="Test",
        )

        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha="test",
            trigger="test",
            findings=[finding],
            reasoning="Test",
            confidence=0.9,
        )

        data = finding.to_dict()
        restored = Finding.from_dict(data)
        assert restored.location == finding.location

        print("   ✓ Data models working")
        checks_passed += 1
    except Exception as e:
        print(f"   ✗ Data model test failed: {e}")
        checks_failed += 1

    # Summary
    print()
    print("=" * 60)
    print(f"Checks: {checks_passed} passed, {checks_failed} failed")
    print("=" * 60)
    print()

    if checks_failed == 0:
        print("✅ System ready!")
        print()
        print("Next steps:")
        print("  python analyze_file.py <file.py>          # Static analysis")
        print("  python analyze_file.py <file.py> --llm    # With LLM")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
