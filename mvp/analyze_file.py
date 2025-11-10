#!/usr/bin/env python3
"""Simple CLI to analyze a Python file with ModuleAgent.

Usage:
    python analyze_file.py <file.py>
    python analyze_file.py <file.py> --llm
"""

import asyncio
import os
import sys
from pathlib import Path

from src.eidolon_mvp.agents.module_agent import ModuleAgent
from src.eidolon_mvp.llm.config import create_llm_from_env
from src.eidolon_mvp.memory.store import MemoryStore


async def analyze_file(file_path: str, use_llm: bool = False):
    """Analyze a Python file."""
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    if not path.suffix == ".py":
        print(f"Error: Not a Python file: {file_path}")
        return 1

    print(f"Analyzing: {file_path}")
    print()

    # Read source
    source_code = path.read_text()
    line_count = len(source_code.split("\n"))
    print(f"  Lines of code: {line_count}")

    # Setup
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/eidolon_mvp")
    store = MemoryStore(db_url)

    try:
        await store.connect()
    except Exception as e:
        print(f"Error: Database connection failed: {e}")
        print("Run: createdb eidolon_mvp && psql eidolon_mvp < SCHEMA.sql")
        return 1

    # LLM setup
    llm = None
    if use_llm:
        llm = create_llm_from_env()
        if llm:
            provider = os.getenv("LLM_PROVIDER", "anthropic")
            print(f"  Using: LLM-enhanced analysis ({provider})")
            if llm.base_url:
                print(f"  Base URL: {llm.base_url}")
            print(f"  Model: {llm.model}")
        else:
            print("  Warning: --llm specified but no API key configured")
            print("  Set ANTHROPIC_API_KEY or OPENAI_API_KEY (see .env.example)")
            print("  Using: Static analysis only")
    else:
        print("  Using: Static analysis only")

    print()

    # Create agent
    agent = ModuleAgent(
        module_path=str(path),
        source_code=source_code,
        memory_store=store,
        llm=llm,
        commit_sha="manual_analysis",
    )

    await store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": str(path), "manual": True}
    )

    # Analyze
    try:
        print("🔍 Running analysis...")
        print()
        findings = await agent.analyze()
        print()

        # Results
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()

        if not findings:
            print("✅ No issues found! Code looks clean.")
        else:
            # Group by severity
            by_severity = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": [],
                "info": [],
            }

            for finding in findings:
                by_severity[finding.severity].append(finding)

            # Show summary
            print(f"Found {len(findings)} issue(s):")
            for severity in ["critical", "high", "medium", "low", "info"]:
                count = len(by_severity[severity])
                if count > 0:
                    emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                        "info": "ℹ️",
                    }[severity]
                    print(f"  {emoji} {severity.upper()}: {count}")

            print()

            # Show details
            for severity in ["critical", "high", "medium", "low", "info"]:
                issues = by_severity[severity]
                if not issues:
                    continue

                print(f"\n{severity.upper()} Issues:")
                print("-" * 70)

                for i, finding in enumerate(issues, 1):
                    print(f"\n{i}. {finding.description}")
                    print(f"   Location: {finding.location}")
                    print(f"   Type: {finding.type}")
                    if finding.suggested_fix:
                        print(f"   Fix: {finding.suggested_fix}")

        print()
        print("=" * 70)

        # Show functions analyzed
        report = agent.report()
        print(f"Functions analyzed: {len(agent.function_agents)}")
        if agent.function_agents:
            print()
            for func_agent in agent.function_agents:
                status = (
                    "✓"
                    if len(func_agent.findings) == 0
                    else f"⚠ {len(func_agent.findings)}"
                )
                print(f"  {status} {func_agent.function_name}")

        print()

        # Memory info
        analyses = await agent.memory.get_analyses()
        if analyses:
            latest = analyses[0]
            print(f"Confidence: {latest.confidence:.0%}")
            print(f"Analysis ID: {latest.id}")

        return 0 if len(findings) == 0 else 1

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        await store.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_file.py <file.py> [--llm]")
        print()
        print("Analyze a Python file for bugs and code quality issues.")
        print()
        print("Options:")
        print("  --llm    Use LLM for deep analysis (requires ANTHROPIC_API_KEY)")
        return 1

    file_path = sys.argv[1]
    use_llm = "--llm" in sys.argv

    return asyncio.run(analyze_file(file_path, use_llm))


if __name__ == "__main__":
    sys.exit(main())
