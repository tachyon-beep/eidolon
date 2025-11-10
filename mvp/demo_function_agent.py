#!/usr/bin/env python3
"""Demo of FunctionAgent analyzing real code.

This demonstrates Week 2 capabilities:
- Static analysis (complexity, null safety, resources)
- Finding storage in memory
- Report generation
"""

import asyncio
import os
from datetime import datetime

from src.eidolon_mvp.agents.function_agent import FunctionAgent
from src.eidolon_mvp.llm.client import LLMClient
from src.eidolon_mvp.memory.store import MemoryStore


# Example functions to analyze
EXAMPLES = {
    "clean": """
def calculate_total(items: list[dict]) -> float:
    '''Calculate total price with proper validation.'''
    if not items:
        return 0.0

    total = 0.0
    for item in items:
        if isinstance(item, dict) and 'price' in item:
            price = item.get('price', 0)
            if isinstance(price, (int, float)) and price >= 0:
                total += price

    return round(total, 2)
""",
    "risky": """
def process_user_data(data):
    '''Function with multiple issues.'''
    # Issue 1: No validation
    user = data.get("user")

    # Issue 2: Potential None access
    if user.is_active:
        # Issue 3: Unclosed file
        f = open("log.txt", "a")
        f.write(user.name)

        # Issue 4: Bare except
        try:
            result = complex_operation(user)
        except:
            pass

    return user.id
""",
    "complex": """
def nested_logic(x, y, z):
    '''Overly complex function.'''
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    if y > z:
                        if x > z:
                            if x > 100:
                                if y > 50:
                                    if z > 25:
                                        return True
    return False
""",
}


async def analyze_example(name: str, code: str, store: MemoryStore, llm=None):
    """Analyze an example function."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {name}")
    print(f"{'='*60}")
    print(code)
    print()

    # Create agent
    agent = FunctionAgent(
        function_id=f"demo.{name}",
        function_name=name,
        source_code=code,
        file_path=f"demo_{name}.py",
        memory_store=store,
        llm=llm,
        commit_sha=f"demo_{name}_v1",
    )

    # Ensure agent exists
    await store.ensure_agent_exists(
        agent.agent_id, "function", {"function_name": name, "demo": True}
    )

    # Analyze
    print("🔍 Running analysis...")
    findings = await agent.analyze()

    # Show results
    if not findings:
        print("✅ No issues found - code looks good!")
    else:
        print(f"Found {len(findings)} issue(s):\n")
        for i, finding in enumerate(findings, 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "info": "ℹ️",
            }
            emoji = severity_emoji.get(finding.severity, "•")

            print(f"{i}. {emoji} [{finding.severity.upper()}] {finding.type}")
            print(f"   Location: {finding.location}")
            print(f"   Issue: {finding.description}")
            if finding.suggested_fix:
                print(f"   Fix: {finding.suggested_fix}")
            print()

    # Show report
    report = agent.report()
    print(f"Summary: {report.summary}")

    # Show memory
    analyses = await agent.memory.get_analyses()
    latest = analyses[0]
    print(f"Confidence: {latest.confidence:.0%}")
    print(f"Stored in memory: analysis #{latest.id}")

    return findings


async def main():
    """Run demo."""
    print("=" * 60)
    print("FunctionAgent Demo - Week 2")
    print("=" * 60)
    print()
    print("This demo shows FunctionAgent analyzing Python functions")
    print("for bugs, security issues, and code quality problems.")
    print()

    # Setup
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/eidolon_mvp")
    print(f"Database: {db_url}")

    store = MemoryStore(db_url)

    try:
        print("Connecting to database...")
        await store.connect()
        print("✓ Connected")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print()
        print("To run this demo:")
        print("  1. createdb eidolon_mvp")
        print("  2. psql eidolon_mvp < SCHEMA.sql")
        print("  3. export DATABASE_URL=postgresql://localhost/eidolon_mvp")
        return

    # Check for LLM (optional)
    llm = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        print("✓ LLM available (Anthropic)")
        llm = LLMClient(provider="anthropic", api_key=api_key)
    else:
        print("ℹ️  LLM not available (set ANTHROPIC_API_KEY for deep analysis)")

    print()

    # Analyze examples
    try:
        # Example 1: Clean code
        await analyze_example("clean", EXAMPLES["clean"], store, llm)

        # Example 2: Risky code
        await analyze_example("risky", EXAMPLES["risky"], store, llm)

        # Example 3: Complex code
        await analyze_example("complex", EXAMPLES["complex"], store, llm)

    finally:
        await store.close()

    print()
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print()
    print("The FunctionAgent successfully:")
    print("  ✓ Analyzed 3 different functions")
    print("  ✓ Found bugs using static analysis")
    print("  ✓ Stored all analyses in persistent memory")
    print("  ✓ Generated confidence scores")
    print()
    print("Next: Week 3 - ModuleAgent that coordinates FunctionAgents")


if __name__ == "__main__":
    asyncio.run(main())
