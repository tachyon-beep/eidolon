"""Tests for agent data models."""

from datetime import datetime

from eidolon_mvp.agents.models import Analysis, Finding, Report
from eidolon_mvp.agents.base import Scope


def test_finding_creation():
    """Test creating a finding."""
    finding = Finding(
        location="src/auth/login.py:42",
        severity="high",
        type="bug",
        description="Null pointer exception possible",
        suggested_fix="Add null check before accessing user.id",
    )

    assert finding.location == "src/auth/login.py:42"
    assert finding.severity == "high"
    assert finding.type == "bug"


def test_finding_to_dict():
    """Test serializing finding to dict."""
    finding = Finding(
        location="test.py:1",
        severity="low",
        type="style",
        description="Test issue",
    )

    data = finding.to_dict()
    assert data["location"] == "test.py:1"
    assert data["severity"] == "low"
    assert data["description"] == "Test issue"


def test_finding_from_dict():
    """Test deserializing finding from dict."""
    data = {
        "location": "test.py:1",
        "severity": "medium",
        "type": "performance",
        "description": "Slow operation",
        "suggested_fix": "Use faster algorithm",
        "code_snippet": "x = slow_func()",
        "agent_id": "function:test",
    }

    finding = Finding.from_dict(data)
    assert finding.location == "test.py:1"
    assert finding.severity == "medium"
    assert finding.suggested_fix == "Use faster algorithm"


def test_analysis_creation():
    """Test creating an analysis."""
    findings = [
        Finding(
            location="test.py:1",
            severity="high",
            type="bug",
            description="Bug 1",
        ),
        Finding(
            location="test.py:2",
            severity="low",
            type="style",
            description="Style issue",
        ),
    ]

    analysis = Analysis(
        timestamp=datetime.utcnow(),
        commit_sha="abc123",
        trigger="initial_audit",
        findings=findings,
        reasoning="Found 2 issues during analysis",
        confidence=0.85,
    )

    assert len(analysis.findings) == 2
    assert analysis.commit_sha == "abc123"
    assert analysis.confidence == 0.85


def test_report_total_findings():
    """Test counting total findings in report tree."""
    # Create parent report with 2 findings
    parent_findings = [
        Finding(location="a.py:1", severity="high", type="bug", description="Bug 1"),
        Finding(location="a.py:2", severity="medium", type="bug", description="Bug 2"),
    ]

    # Create child reports with findings
    child1_findings = [
        Finding(location="b.py:1", severity="low", type="style", description="Style 1"),
    ]
    child2_findings = [
        Finding(location="c.py:1", severity="high", type="bug", description="Bug 3"),
        Finding(location="c.py:2", severity="medium", type="bug", description="Bug 4"),
    ]

    child1 = Report(
        agent_id="child1",
        scope=Scope(type="function", id="test1"),
        findings=child1_findings,
        summary="Child 1",
    )

    child2 = Report(
        agent_id="child2",
        scope=Scope(type="function", id="test2"),
        findings=child2_findings,
        summary="Child 2",
    )

    parent = Report(
        agent_id="parent",
        scope=Scope(type="module", path="test.py"),
        findings=parent_findings,
        summary="Parent",
        children=[child1, child2],
    )

    # Parent has 2, child1 has 1, child2 has 2 = 5 total
    assert parent.total_findings() == 5


def test_report_findings_by_severity():
    """Test grouping findings by severity."""
    findings = [
        Finding(location="a.py:1", severity="critical", type="bug", description="1"),
        Finding(location="a.py:2", severity="high", type="bug", description="2"),
        Finding(location="a.py:3", severity="high", type="bug", description="3"),
        Finding(location="a.py:4", severity="medium", type="bug", description="4"),
        Finding(location="a.py:5", severity="low", type="bug", description="5"),
        Finding(location="a.py:6", severity="low", type="bug", description="6"),
        Finding(location="a.py:7", severity="low", type="bug", description="7"),
    ]

    report = Report(
        agent_id="test",
        scope=Scope(type="module", path="test.py"),
        findings=findings,
        summary="Test",
    )

    counts = report.findings_by_severity()
    assert counts["critical"] == 1
    assert counts["high"] == 2
    assert counts["medium"] == 1
    assert counts["low"] == 3
    assert counts["info"] == 0
