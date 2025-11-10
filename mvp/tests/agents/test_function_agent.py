"""Tests for FunctionAgent."""

import pytest

from eidolon_mvp.agents.function_agent import FunctionAgent


@pytest.mark.asyncio
async def test_function_agent_creation(memory_store):
    """Test creating a function agent."""
    code = """
def example_function(x):
    return x * 2
"""

    agent = FunctionAgent(
        function_id="test.example_function",
        function_name="example_function",
        source_code=code,
        file_path="test.py",
        memory_store=memory_store,
        commit_sha="test123",
    )

    assert agent.agent_id == "function:test.example_function"
    assert agent.function_name == "example_function"
    assert agent.scope.type == "function"


@pytest.mark.asyncio
async def test_function_agent_static_analysis(memory_store):
    """Test static analysis without LLM."""
    code = """
def risky_function():
    f = open("test.txt")  # Bad: no context manager
    data = f.read()
    return data
"""

    agent = FunctionAgent(
        function_id="test.risky_function",
        function_name="risky_function",
        source_code=code,
        file_path="test.py",
        memory_store=memory_store,
        llm=None,  # No LLM
    )

    findings = await agent.analyze()

    # Should find the unclosed file
    assert len(findings) > 0
    assert any("context manager" in f.description.lower() for f in findings)


@pytest.mark.asyncio
async def test_function_agent_stores_analysis(memory_store):
    """Test that analysis is stored in memory."""
    code = """
def simple_function(x):
    return x + 1
"""

    agent = FunctionAgent(
        function_id="test.simple_function",
        function_name="simple_function",
        source_code=code,
        file_path="test.py",
        memory_store=memory_store,
        commit_sha="abc123",
    )

    # Ensure agent exists in DB
    await memory_store.ensure_agent_exists(
        agent.agent_id, "function", {"function_name": "simple_function"}
    )

    findings = await agent.analyze()

    # Should store analysis in memory
    analyses = await agent.memory.get_analyses()
    assert len(analyses) > 0
    assert analyses[0].commit_sha == "abc123"


@pytest.mark.asyncio
async def test_function_agent_report(memory_store):
    """Test generating report."""
    code = """
def test_function():
    x = 1
    y = 2
    return x + y
"""

    agent = FunctionAgent(
        function_id="test.test_function",
        function_name="test_function",
        source_code=code,
        file_path="test.py",
        memory_store=memory_store,
    )

    await agent.analyze()
    report = agent.report()

    assert report.agent_id == "function:test.test_function"
    assert report.scope.type == "function"
    assert isinstance(report.summary, str)


@pytest.mark.asyncio
async def test_function_agent_complex_code(memory_store):
    """Test analyzing more complex code."""
    code = """
def complex_function(data):
    # Multiple issues here
    user = data.get("user")  # Might be None
    if user.is_active:  # Potential None access
        try:
            result = process(user)
        except:  # Bare except
            pass
    return None
"""

    agent = FunctionAgent(
        function_id="test.complex_function",
        function_name="complex_function",
        source_code=code,
        file_path="test.py",
        memory_store=memory_store,
    )

    findings = await agent.analyze()

    # Should find multiple issues
    assert len(findings) >= 2

    # Should have various severities
    severities = {f.severity for f in findings}
    assert len(severities) > 0


@pytest.mark.asyncio
async def test_function_agent_confidence_scoring(memory_store):
    """Test confidence scoring."""
    clean_code = """
def clean_function(x: int) -> int:
    if x > 0:
        return x * 2
    return 0
"""

    agent = FunctionAgent(
        function_id="test.clean_function",
        function_name="clean_function",
        source_code=clean_code,
        file_path="test.py",
        memory_store=memory_store,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "function", {"function_name": "clean_function"}
    )

    await agent.analyze()

    # Get stored analysis
    analyses = await agent.memory.get_analyses()
    assert len(analyses) > 0

    # Clean code should have high confidence
    assert analyses[0].confidence > 0.7
