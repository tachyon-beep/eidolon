import asyncio
from types import SimpleNamespace

import pytest

from eidolon.agents.orchestrator import AgentOrchestrator
from eidolon.llm_providers.mock_provider import MockLLMProvider
from eidolon.storage.database import Database
from eidolon.models import Agent, AgentScope, AgentStatus, Card, CardType, CardStatus


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

    async def create_card(self, card: Card):
        card.id = card.id or f"CARD-{len(self.cards)+1}"
        self.cards[card.id] = card
        return card

    async def get_card(self, card_id: str):
        return self.cards.get(card_id)


@pytest.mark.asyncio
async def test_analyze_codebase_small_project(tmp_path, monkeypatch):
    # Create a tiny project with one module and one function
    mod = tmp_path / "sample.py"
    mod.write_text(
        """
def add(a, b):
    return a + b
"""
    )

    db = FakeDB()
    orch = AgentOrchestrator(
        db=db,
        llm_provider=MockLLMProvider(),
        enable_cache=False,
        max_concurrent_modules=1,
        max_concurrent_functions=1,
    )
    # Skip expensive AI work by patching analysis methods to no-op
    async def no_op(*args, **kwargs):
        return None

    monkeypatch.setattr(orch, "_run_function_analysis", no_op)
    monkeypatch.setattr(orch, "_run_module_analysis", no_op)
    monkeypatch.setattr(orch, "_run_class_analysis", no_op)
    monkeypatch.setattr(orch, "_run_system_analysis", no_op)

    await orch.initialize()
    system_agent = await orch.analyze_codebase(str(tmp_path))

    # Agents persisted, progress tracked
    assert isinstance(system_agent, Agent)
    assert system_agent.scope == AgentScope.SYSTEM
    assert orch.progress["completed_modules"] == orch.progress["total_modules"]
    assert orch.progress["completed_functions"] == orch.progress["total_functions"]
