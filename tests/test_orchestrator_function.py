import asyncio
from types import SimpleNamespace

import pytest

from eidolon.agents.orchestrator import AgentOrchestrator
from eidolon.llm_providers import LLMResponse
from eidolon.llm_providers.mock_provider import MockLLMProvider
from eidolon.storage.database import Database
from eidolon.models import Agent, AgentScope, AgentStatus, Card


class FakeDB(Database):
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.agents = {}
        self.cards = {}

    async def create_agent(self, agent: Agent):
        agent.id = agent.id or f"AGN-{len(self.agents)+1}"
        self.agents[agent.id] = agent
        return agent

    async def update_agent(self, agent: Agent):
        self.agents[agent.id] = agent
        return agent

    async def get_agent(self, agent_id: str):
        return self.agents.get(agent_id)

    async def create_card(self, card: Card):
        card.id = card.id or f"CARD-{len(self.cards)+1}"
        self.cards[card.id] = card
        return card

    async def get_card(self, card_id: str):
        return self.cards.get(card_id)


@pytest.mark.asyncio
async def test_run_function_analysis_creates_card(tmp_path, monkeypatch):
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=False)

    # Patch AI call to return deterministic content
    async def fake_ai_call(max_tokens, messages, estimated_tokens=1000):
        return LLMResponse(
            content="## Issues Found\n- Problem: bug\n**Fix:**\n```python\ndef foo():\n    return 1\n```",
            input_tokens=10,
            output_tokens=5,
            model="mock",
        )

    monkeypatch.setattr(orch, "_call_ai_with_resilience", fake_ai_call)

    # Prepare file and function info
    file_path = tmp_path / "mod.py"
    file_path.write_text("def foo():\n    return 0\n")

    module_info = SimpleNamespace(file_path=str(file_path))
    func_info = SimpleNamespace(
        name="foo",
        line_start=1,
        line_end=2,
        complexity=1,
        is_async=False,
        calls=[],
        called_by=[],
    )

    agent = Agent(id="", scope=AgentScope.FUNCTION, target="mod.py::foo", status=AgentStatus.ANALYZING)
    agent = await db.create_agent(agent)

    orch.call_graph = {"functions": {}}
    await orch._run_function_analysis(agent, module_info, func_info)

    # Card should be created
    assert agent.cards_created
    card_id = agent.cards_created[0]
    assert await db.get_card(card_id)


@pytest.mark.asyncio
async def test_get_agent_hierarchy(tmp_path):
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=False)

    root = Agent(id="root", scope=AgentScope.SYSTEM, target="repo", status=AgentStatus.COMPLETED, children_ids=["child"])
    child = Agent(id="child", scope=AgentScope.MODULE, target="mod", status=AgentStatus.COMPLETED, children_ids=[])
    await db.create_agent(root)
    await db.create_agent(child)

    tree = await orch.get_agent_hierarchy("root")
    assert tree["id"] == "root"
    assert tree["children"][0]["id"] == "child"
