import pytest

from eidolon.linting_agent import LintingAgent, LintingResult
from eidolon.llm_providers.mock_provider import MockLLMProvider


def test_tool_availability_check(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output=True, timeout=5):
        calls.append(cmd[0])
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)

    agent = LintingAgent(llm_provider=None, use_ruff=True, use_mypy=True)
    assert agent.ruff_available is False
    assert agent.mypy_available is False
    assert calls == ["ruff", "mypy"]


@pytest.mark.asyncio
async def test_linting_agent_without_tools(monkeypatch):
    agent = LintingAgent(llm_provider=None, use_ruff=False, use_mypy=False, use_llm_fixes=False)

    result = await agent.lint_and_fix("def add(a, b):\n    return a+b\n", filename="tmp.py")
    assert isinstance(result, LintingResult)
    assert result.fixed_code.startswith("def add")
    assert result.total_issues == 0


@pytest.mark.asyncio
async def test_linting_agent_llm_fix(monkeypatch):
    provider = MockLLMProvider()
    agent = LintingAgent(llm_provider=provider, use_ruff=False, use_mypy=False, use_llm_fixes=True)

    async def fake_completion(messages, max_tokens=4096, temperature=0.0, response_format=None, **kwargs):
        from eidolon.llm_providers import LLMResponse
        content = """{
            "fixed_code": "def add(a: int, b: int) -> int:\\n    return a + b",
            "fixes_applied": ["add type hints"]
        }"""
        return LLMResponse(content=content, input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    # Seed an unfixed error to trigger LLM path
    result = await agent._llm_fix_issues(
        code="def add(a,b): return a+b",
        issues=[],
        filename="tmp.py",
    )
    # when no issues, should return original code unchanged
    assert result[0].startswith("def add")

    # force issues so LLM is used
    issues = []
    from eidolon.linting_agent import LintIssue

    issues.append(LintIssue(tool="ruff", severity="error", code="E999", message="bad", line=1, column=1, fixable=False))
    fixed_code, llm_result = await agent._llm_fix_issues("def add(a,b): return a+b", issues, "tmp.py")
    assert "a: int" in fixed_code
    assert llm_result["fixed_count"] >= 1
