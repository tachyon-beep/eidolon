"""Tests for ModuleAgent."""

import pytest

from eidolon_mvp.agents.module_agent import ModuleAgent


SAMPLE_MODULE = """
'''Module for user authentication.'''

def login(username, password):
    '''Authenticate user.'''
    if username and password:
        return True
    return False

def logout(session):
    '''End user session.'''
    session.clear()
    return True

def validate_token(token):
    '''Validate auth token.'''
    if not token:
        return False

    # Potential issue: no try/except
    decoded = decode_jwt(token)
    return decoded.is_valid()
"""


RISKY_MODULE = """
def process_data(data):
    user = data.get("user")
    return user.name  # None risk

def open_file(path):
    f = open(path)  # Unclosed
    return f.read()

def bad_error_handling():
    try:
        dangerous()
    except:  # Bare except
        pass
"""


@pytest.mark.asyncio
async def test_module_agent_creation(memory_store):
    """Test creating a module agent."""
    agent = ModuleAgent(
        module_path="src/auth.py",
        source_code=SAMPLE_MODULE,
        memory_store=memory_store,
        commit_sha="test123",
    )

    assert agent.agent_id == "module:src/auth.py"
    assert agent.scope.type == "module"
    assert agent.module_path == "src/auth.py"


@pytest.mark.asyncio
async def test_module_agent_finds_functions(memory_store):
    """Test that module agent finds all functions."""
    agent = ModuleAgent(
        module_path="src/auth.py",
        source_code=SAMPLE_MODULE,
        memory_store=memory_store,
    )

    functions = agent._extract_functions()

    # Should find 3 functions
    assert len(functions) == 3
    func_names = [name for name, _ in functions]
    assert "login" in func_names
    assert "logout" in func_names
    assert "validate_token" in func_names


@pytest.mark.asyncio
async def test_module_agent_spawns_function_agents(memory_store):
    """Test that module agent spawns function agents."""
    agent = ModuleAgent(
        module_path="src/auth.py",
        source_code=SAMPLE_MODULE,
        memory_store=memory_store,
    )

    # Ensure module agent exists
    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/auth.py"}
    )

    findings = await agent.analyze()

    # Should have spawned 3 function agents
    assert len(agent.function_agents) == 3

    # Each function agent should have analyzed
    for func_agent in agent.function_agents:
        assert func_agent.agent_id.startswith("function:")


@pytest.mark.asyncio
async def test_module_agent_aggregates_findings(memory_store):
    """Test that module agent aggregates findings from functions."""
    agent = ModuleAgent(
        module_path="src/risky.py",
        source_code=RISKY_MODULE,
        memory_store=memory_store,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/risky.py"}
    )

    findings = await agent.analyze()

    # Should find issues from multiple functions
    assert len(findings) > 0

    # Should have findings from different functions
    agent_ids = {f.agent_id for f in findings}
    assert len(agent_ids) > 1  # Module + at least one function


@pytest.mark.asyncio
async def test_module_agent_hierarchical_report(memory_store):
    """Test hierarchical report generation."""
    agent = ModuleAgent(
        module_path="src/auth.py",
        source_code=SAMPLE_MODULE,
        memory_store=memory_store,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/auth.py"}
    )

    await agent.analyze()
    report = agent.report()

    # Should have module report
    assert report.agent_id == "module:src/auth.py"

    # Should have child reports from functions
    assert len(report.children) == 3

    # Total findings should include module + all children
    total = report.total_findings()
    assert total >= len(report.findings)


@pytest.mark.asyncio
async def test_module_agent_module_level_checks(memory_store):
    """Test module-level architecture checks."""
    # Module with wildcard import
    bad_module = """
from os import *

def test():
    pass
"""

    agent = ModuleAgent(
        module_path="src/bad.py",
        source_code=bad_module,
        memory_store=memory_store,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/bad.py"}
    )

    findings = await agent.analyze()

    # Should find wildcard import issue
    wildcard_findings = [f for f in findings if "wildcard" in f.description.lower()]
    assert len(wildcard_findings) > 0


@pytest.mark.asyncio
async def test_module_agent_parallel_execution(memory_store):
    """Test that function agents run in parallel."""
    # Module with multiple functions
    multi_func = """
def func1():
    pass

def func2():
    pass

def func3():
    pass

def func4():
    pass

def func5():
    pass
"""

    agent = ModuleAgent(
        module_path="src/multi.py",
        source_code=multi_func,
        memory_store=memory_store,
        max_concurrent=3,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/multi.py"}
    )

    findings = await agent.analyze()

    # All 5 functions should be analyzed
    assert len(agent.function_agents) == 5


@pytest.mark.asyncio
async def test_module_agent_stores_analysis(memory_store):
    """Test that module analysis is stored in memory."""
    agent = ModuleAgent(
        module_path="src/auth.py",
        source_code=SAMPLE_MODULE,
        memory_store=memory_store,
        commit_sha="test456",
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/auth.py"}
    )

    await agent.analyze()

    # Should store analysis in memory
    analyses = await agent.memory.get_analyses()
    assert len(analyses) > 0
    assert analyses[0].commit_sha == "test456"
    assert analyses[0].metadata["function_count"] == 3


@pytest.mark.asyncio
async def test_module_agent_missing_docstring(memory_store):
    """Test detection of missing module docstring."""
    no_docstring = """
def test():
    pass
"""

    agent = ModuleAgent(
        module_path="src/nodoc.py",
        source_code=no_docstring,
        memory_store=memory_store,
    )

    await memory_store.ensure_agent_exists(
        agent.agent_id, "module", {"module_path": "src/nodoc.py"}
    )

    findings = await agent.analyze()

    # Should find missing docstring
    docstring_findings = [f for f in findings if "docstring" in f.description.lower()]
    assert len(docstring_findings) > 0
