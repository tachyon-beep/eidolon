import json
import pytest

from eidolon.test_generator import SuiteGeneratorAgent, SuiteRunnerAgent
from eidolon.llm_providers.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_generate_function_tests_parses_json(monkeypatch):
    provider = MockLLMProvider()
    generator = SuiteGeneratorAgent(provider)

    expected = {
        "test_code": "def test_x():\n    assert True",
        "test_count": 2,
        "coverage_estimate": 80.0,
        "explanation": "good",
    }

    async def fake_completion(messages, max_tokens=2048, temperature=0.1, **kwargs):
        from eidolon.llm_providers import LLMResponse
        return LLMResponse(content=json.dumps(expected), input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    result = await generator.generate_function_tests(
        function_code="def add(a,b): return a+b",
        function_name="add",
        module_path="math.py",
    )

    assert result["test_code"] == expected["test_code"]
    assert result["test_count"] == 2
    assert result["coverage_estimate"] == 80.0


@pytest.mark.asyncio
async def test_generate_function_tests_fallback(monkeypatch):
    provider = MockLLMProvider()
    generator = SuiteGeneratorAgent(provider)

    async def fake_completion(messages, max_tokens=2048, temperature=0.1, **kwargs):
        from eidolon.llm_providers import LLMResponse
        return LLMResponse(content="not json", input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    result = await generator.generate_function_tests(
        function_code="def add(a,b): return a+b",
        function_name="add",
        module_path="math.py",
    )

    assert "test_code" in result
    assert result["test_count"] == 1


def test_test_runner_handles_missing_file(tmp_path):
    runner = SuiteRunnerAgent(project_path=tmp_path)
    result = runner.run_tests("missing.py")
    assert result["success"] is False
    assert result["total"] == 0
