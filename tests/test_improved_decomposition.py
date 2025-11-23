import json
import pytest

from eidolon.planning.improved_decomposition import (
    ImprovedSystemDecomposer,
    extract_json_from_response,
)
from eidolon.models import TaskType
from eidolon.llm_providers.mock_provider import MockLLMProvider


def test_extract_json_from_response_variants():
    direct = extract_json_from_response('{"a":1}')
    assert direct == {"a": 1}

    code_block = extract_json_from_response("```json\n{\"b\":2}\n```")
    assert code_block == {"b": 2}

    sloppy = extract_json_from_response("noise ```\n{\"c\":3}\n```")
    assert sloppy == {"c": 3}

    brace = extract_json_from_response("start {\"d\":4} end")
    assert brace == {"d": 4}

    assert extract_json_from_response("no json") is None


@pytest.mark.asyncio
async def test_improved_system_decomposer_parses_llm_output(monkeypatch):
    provider = MockLLMProvider()
    decomposer = ImprovedSystemDecomposer(llm_provider=provider)

    expected = {
        "understanding": "Do something",
        "subsystem_tasks": [
            {
                "subsystem": "api",
                "instruction": "Add endpoint",
                "type": "create_new",
                "priority": "critical",
                "dependencies": [],
                "complexity": "low",
            }
        ],
        "overall_complexity": "low",
    }

    async def fake_completion(messages, max_tokens=1024, temperature=0.0, response_format=None, **kwargs):
        from eidolon.llm_providers import LLMResponse

        return LLMResponse(
            content=json.dumps(expected),
            input_tokens=0,
            output_tokens=0,
            model="mock",
        )

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    tasks = await decomposer.decompose(
        user_request="Add endpoint",
        project_path="/repo",
        subsystems=["api"],
    )

    assert len(tasks) == 1
    assert tasks[0].target == "api"
    assert tasks[0].type == "create_new"
