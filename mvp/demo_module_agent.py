#!/usr/bin/env python3
"""Demo of ModuleAgent analyzing complete Python modules.

This demonstrates Week 3 capabilities:
- Parallel execution of multiple FunctionAgents
- Module-level architecture checks
- Hierarchical reporting
- Agent hierarchy tracking
"""

import asyncio
import os

from src.eidolon_mvp.agents.module_agent import ModuleAgent
from src.eidolon_mvp.llm.client import LLMClient
from src.eidolon_mvp.memory.store import MemoryStore


# Example module with multiple functions
EXAMPLE_MODULE = """
'''User authentication and session management.'''

import hashlib
import jwt
from typing import Optional


def hash_password(password: str) -> str:
    '''Hash password using SHA256.'''
    if not password:
        raise ValueError("Password cannot be empty")

    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    '''Verify password against hash.'''
    return hash_password(password) == hashed


def login(username: str, password: str) -> Optional[dict]:
    '''Authenticate user and return session.'''
    # Issue: No validation
    user = get_user(username)

    # Issue: Potential None access
    if user.is_active:
        if verify_password(password, user.password_hash):
            return create_session(user)

    return None


def logout(session_id: str) -> bool:
    '''End user session.'''
    try:
        session = get_session(session_id)
        session.delete()
        return True
    except:  # Issue: Bare except
        return False


def validate_token(token: str) -> bool:
    '''Validate JWT token.'''
    if not token:
        return False

    try:
        decoded = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
        return decoded.get("exp") > time.time()
    except jwt.InvalidTokenError:
        return False


def create_session(user):
    '''Create new session.'''
    # Issue: Too complex
    if user:
        if user.is_active:
            if not user.is_locked:
                if user.email_verified:
                    if user.two_factor_enabled:
                        if user.two_factor_verified:
                            session = Session()
                            session.user_id = user.id
                            session.save()
                            return session
    return None


def write_audit_log(action: str, user_id: int) -> None:
    '''Write action to audit log.'''
    # Issue: Unclosed file
    f = open("audit.log", "a")
    f.write(f"{action},{user_id}\\n")
"""


async def analyze_module(name: str, code: str, store: MemoryStore, llm=None):
    """Analyze a module."""
    print(f"\n{'='*70}")
    print(f"Analyzing Module: {name}")
    print(f"{'='*70}")
    print()

    # Create agent
    agent = ModuleAgent(
        module_path=f"src/{name}.py",
        source_code=code,
        memory_store=store,
        llm=llm,
        commit_sha=f"demo_{name}_v1",
        max_concurrent=5,
    )

    # Ensure agent exists
    await store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": f"src/{name}.py", "demo": True}
    )

    # Analyze
    print("🔍 Analyzing module...")
    print()
    findings = await agent.analyze()
    print()

    # Show report
    report = agent.report()

    print(f"{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print()
    print(f"Module: {report.scope.path}")
    print(f"Functions analyzed: {len(agent.function_agents)}")
    print(f"Total findings: {report.total_findings()}")
    print()

    # Show findings by severity
    by_severity = report.findings_by_severity()
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "ℹ️",
    }

    print("Findings by severity:")
    for severity in ["critical", "high", "medium", "low", "info"]:
        count = by_severity.get(severity, 0)
        if count > 0:
            emoji = severity_emoji.get(severity, "•")
            print(f"  {emoji} {severity.upper()}: {count}")
    print()

    # Show module-level issues
    module_findings = [f for f in findings if f.agent_id == agent.agent_id]
    if module_findings:
        print(f"Module-level issues ({len(module_findings)}):")
        for finding in module_findings:
            print(f"  • {finding.description}")
        print()

    # Show functions with issues
    print("Functions with issues:")
    for func_agent in agent.function_agents:
        if len(func_agent.findings) > 0:
            print(
                f"  • {func_agent.function_name}: {len(func_agent.findings)} issue(s)"
            )
    print()

    # Show hierarchical report summary
    print("Hierarchical Summary:")
    print(f"  Module: {report.agent_id}")
    print(f"  Children: {len(report.children)} function agents")
    for child in report.children:
        status = "✓" if len(child.findings) == 0 else f"⚠ {len(child.findings)}"
        print(f"    - {child.scope.id}: {status}")
    print()

    # Show memory info
    analyses = await agent.memory.get_analyses()
    latest = analyses[0]
    print(f"Analysis stored with ID: {latest.id}")
    print(f"Confidence: {latest.confidence:.0%}")
    print(f"Reasoning: {latest.reasoning}")

    return report


async def main():
    """Run demo."""
    print("=" * 70)
    print("ModuleAgent Demo - Week 3")
    print("=" * 70)
    print()
    print("This demo shows ModuleAgent coordinating multiple FunctionAgents")
    print("to analyze a complete Python module in parallel.")
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

    # Analyze module
    try:
        report = await analyze_module("auth", EXAMPLE_MODULE, store, llm)

        # Show total statistics
        print()
        print("=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print()
        print("The ModuleAgent successfully:")
        print(f"  ✓ Spawned {len(report.children)} FunctionAgents")
        print("  ✓ Executed them in parallel")
        print(f"  ✓ Found {report.total_findings()} issues across the module")
        print("  ✓ Performed module-level architecture checks")
        print("  ✓ Generated hierarchical report")
        print("  ✓ Stored all analyses in persistent memory")
        print()
        print("This demonstrates the hierarchical agent system:")
        print("  Module Agent → Function Agents → Findings")
        print()

    finally:
        await store.close()

    print("Next: Point this at a real codebase! 🚀")


if __name__ == "__main__":
    asyncio.run(main())
