import pytest

from eidolon.agents.implementation_orchestrator import ImplementationOrchestrator
from eidolon.llm_providers.mock_provider import MockLLMProvider
from eidolon.storage.database import Database
from eidolon.models import Task


class FakeDB(Database):
    async def create_agent(self, agent):
        agent.id = agent.id or "AGN-1"
        return agent

    async def update_agent(self, agent):
        return agent

    async def create_card(self, card):
        return card


@pytest.mark.asyncio
async def test_implementation_orchestrator_initializes_components(tmp_path):
    db = FakeDB()
    orch = ImplementationOrchestrator(
        db=db,
        llm_provider=MockLLMProvider(),
        project_path=str(tmp_path),
        enable_testing=False,
        enable_rollback=False,
    )
    assert orch.project_path == str(tmp_path)
    assert orch.enable_testing is False
    assert orch.enable_rollback is False
    assert orch.task_graph.tasks == {}


@pytest.mark.asyncio
async def test_task_graph_addition(tmp_path, monkeypatch):
    db = FakeDB()
    orch = ImplementationOrchestrator(
        db=db,
        llm_provider=MockLLMProvider(),
        project_path=str(tmp_path),
        enable_testing=False,
        enable_rollback=False,
    )

    # Patch decomposers to return no tasks to keep it fast
    async def empty_decompose(*args, **kwargs):
        return []

    monkeypatch.setattr(orch.system_decomposer, "decompose", empty_decompose)
    monkeypatch.setattr(orch.subsystem_decomposer, "decompose", empty_decompose)
    monkeypatch.setattr(orch.module_decomposer, "decompose", empty_decompose)
    monkeypatch.setattr(orch.class_decomposer, "decompose", empty_decompose)
    async def empty_plan(*args, **kwargs):
        return []

    monkeypatch.setattr(orch.function_planner, "plan_function", empty_plan, raising=False)

    result = await orch.implement_feature("Do nothing", {})
    assert result["status"] == "completed"
    assert result["tasks_completed"] >= 1
