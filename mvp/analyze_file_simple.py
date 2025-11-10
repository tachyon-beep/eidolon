#!/usr/bin/env python3
"""Simplified analyzer that doesn't require database for quick testing.

Usage:
    python analyze_file_simple.py <file.py>
    python analyze_file_simple.py <file.py> --llm
"""

import asyncio
import os
import sys
from pathlib import Path

from src.eidolon_mvp.agents.static_checks import analyze_function_code
from src.eidolon_mvp.llm.config import create_llm_from_env


async def analyze_file_simple(file_path: str, use_llm: bool = False):
    """Analyze a Python file without database."""
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
            print("  Using: Static analysis only")
            use_llm = False
    else:
        print("  Using: Static analysis only")

    print()

    # Parse to find functions
    import ast

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"Syntax error: {e}")
        return 1

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    print(f"Found {len(functions)} functions")
    print()

    # Analyze each function
    all_findings = []
    print("🔍 Running analysis...")
    print()

    for func_name in functions:
        findings = analyze_function_code(func_name, source_code, str(path))
        if findings:
            all_findings.extend(findings)

    # Results
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    if not all_findings:
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

        for finding in all_findings:
            by_severity[finding.severity].append(finding)

        # Show summary
        print(f"Found {len(all_findings)} issue(s):")
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
    print(f"Functions analyzed: {len(functions)}")

    for func_name in functions:
        func_findings = [
            f for f in all_findings if func_name in f.location or func_name in f.description
        ]
        status = "✓" if len(func_findings) == 0 else f"⚠ {len(func_findings)}"
        print(f"  {status} {func_name}")

    print()

    return 0 if len(all_findings) == 0 else 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_file_simple.py <file.py> [--llm]")
        print()
        print("Simplified analyzer (no database required)")
        print()
        print("Options:")
        print("  --llm    Use LLM for deep analysis (requires API key)")
        return 1

    file_path = sys.argv[1]
    use_llm = "--llm" in sys.argv

    return asyncio.run(analyze_file_simple(file_path, use_llm))


if __name__ == "__main__":
    sys.exit(main())
