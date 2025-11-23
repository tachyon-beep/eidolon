import json
import pytest

from eidolon.planning.decomposition import SystemDecomposer
from eidolon.llm_providers.mock_provider import MockLLMProvider
from eidolon.models import TaskType


@pytest.mark.asyncio
async def test_system_decomposer_generates_tasks(monkeypatch):
    provider = MockLLMProvider()
    decomposer = SystemDecomposer(
        llm_provider=provider,
        use_intelligent_selection=False,
        use_review_loop=False,
    )

    fake_plan = {
        "understanding": "Build auth",
        "subsystem_tasks": [
            {
                "subsystem": "api",
                "instruction": "Add login route",
                "type": "create_new",
                "priority": "high",
                "dependencies": [],
                "complexity": "medium",
            },
            {
                "subsystem": "services",
                "instruction": "Add AuthService",
                "type": "create_new",
                "priority": "critical",
                "dependencies": ["models"],
                "complexity": "medium",
            },
        ],
        "overall_complexity": "medium",
    }

    async def fake_completion(messages, max_tokens=1024, temperature=0.0, **kwargs):
        from eidolon.llm_providers import LLMResponse

        return LLMResponse(
            content=json.dumps(fake_plan),
            input_tokens=0,
            output_tokens=0,
            model="mock",
        )

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    tasks = await decomposer.decompose(
        user_request="Add auth",
        project_path="/repo",
        subsystems=["api", "services"],
    )

    assert len(tasks) == 2
    targets = {t.target for t in tasks}
    assert targets == {"api", "services"}
    assert tasks[0].type == TaskType.CREATE_NEW
    assert tasks[1].type == TaskType.CREATE_NEW
    assert all(isinstance(t.dependencies, list) for t in tasks)
