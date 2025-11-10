"""Tests for base agent functionality."""

from datetime import datetime

import pytest

from eidolon_mvp.agents.base import Agent, Scope
from eidolon_mvp.agents.models import Analysis, Finding


class TestAgent(Agent):
    """Simple test agent."""

    async def analyze(self) -> list[Finding]:
        """Run fake analysis."""
        findings = [
            Finding(
                location=f"{self.scope.path}:1",
                severity="medium",
                type="bug",
                description="Test finding",
                agent_id=self.agent_id,
            )
        ]

        # Store in memory
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha="test123",
            trigger="test",
            findings=findings,
            reasoning="This is a test analysis",
            confidence=0.9,
        )

        await self.memory.record_analysis(analysis)
        self.findings = findings

        return findings


@pytest.mark.asyncio
async def test_agent_creation(memory_store):
    """Test creating an agent."""
    scope = Scope(type="module", path="test.py")
    agent = TestAgent(
        agent_id="test:module:test.py",
        scope=scope,
        memory_store=memory_store,
    )

    assert agent.agent_id == "test:module:test.py"
    assert agent.scope.type == "module"
    assert agent.scope.path == "test.py"


@pytest.mark.asyncio
async def test_agent_analyze(memory_store):
    """Test agent analysis."""
    scope = Scope(type="module", path="test.py")
    agent = TestAgent(
        agent_id="test:module:test.py",
        scope=scope,
        memory_store=memory_store,
    )

    findings = await agent.analyze()

    assert len(findings) == 1
    assert findings[0].location == "test.py:1"
    assert findings[0].severity == "medium"


@pytest.mark.asyncio
async def test_agent_report(memory_store):
    """Test agent report generation."""
    scope = Scope(type="module", path="test.py")
    agent = TestAgent(
        agent_id="test:module:test.py",
        scope=scope,
        memory_store=memory_store,
    )

    await agent.analyze()
    report = agent.report()

    assert report.agent_id == "test:module:test.py"
    assert len(report.findings) == 1
    assert "1 medium" in report.summary


def test_scope_str():
    """Test scope string representation."""
    scope1 = Scope(type="function", id="auth.login.validate")
    assert str(scope1) == "function:auth.login.validate"

    scope2 = Scope(type="module", path="src/auth/login.py")
    assert str(scope2) == "module:src/auth/login.py"

    scope3 = Scope(type="system")
    assert str(scope3) == "system:unknown"
