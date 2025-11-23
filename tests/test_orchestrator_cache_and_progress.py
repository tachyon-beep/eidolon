import asyncio
from types import SimpleNamespace

import pytest

from eidolon.agents.orchestrator import AgentOrchestrator
from eidolon.cache import CacheManager
from eidolon.cache.cache_manager import CacheEntry
from eidolon.storage.database import Database
from eidolon.llm_providers.mock_provider import MockLLMProvider
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

    async def create_card(self, card: Card):
        card.id = card.id or f"CARD-{len(self.cards)+1}"
        self.cards[card.id] = card
        return card

    async def get_card(self, card_id: str):
        return self.cards.get(card_id)


@pytest.mark.asyncio
async def test_function_agent_cache_hit(monkeypatch, tmp_path):
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=True)

    # Fake cache with preset entry
    cache = CacheManager(db_path=":memory:")

    async def fake_get_cached_result(file_path, scope, target):
        return CacheEntry(
            id="key",
            file_path=file_path,
            file_hash="hash",
            scope=scope,
            target=target,
            findings=["found"],
            cards_data=[],
            metrics={},
            created_at=0,
            last_accessed=0,
            access_count=1,
        )

    cache.get_cached_result = fake_get_cached_result  # type: ignore
    orch.cache = cache

    # Minimal ModuleInfo/FunctionInfo with required attrs
    module_info = SimpleNamespace(
        file_path=str(tmp_path / "mod.py"),
        functions=[],
        classes=[],
    )
    func_info = SimpleNamespace(
        name="foo",
        complexity=1,
        line_start=1,
        line_end=1,
        is_async=False,
    )

    agent = await orch._deploy_function_agent("parent", module_info, "foo", func_info)
    assert agent.status == AgentStatus.COMPLETED
    assert orch.progress["cache_hits"] == 1
    assert orch.progress["completed_functions"] == 1


def test_get_progress_percentage():
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=False)
    orch.progress = {
        "total_functions": 4,
        "completed_functions": 2,
        "total_modules": 1,
        "completed_modules": 0,
        "errors": [],
        "cache_hits": 0,
        "cache_misses": 0,
    }
    prog = orch.get_progress()
    assert prog["percentage"] == 50
