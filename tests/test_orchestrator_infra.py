import pytest

from eidolon.agents.orchestrator import AgentOrchestrator
from eidolon.cache import CacheManager
from eidolon.storage.database import Database
from eidolon.llm_providers.mock_provider import MockLLMProvider


class FakeDB(Database):
    def __init__(self):
        super().__init__(db_path=":memory:")
        self.agents = {}
        self.cards = {}

    async def connect(self):
        self.connected = True

    async def create_agent(self, agent):
        agent.id = agent.id or "AGN-MOD-0001"
        self.agents[agent.id] = agent
        return agent

    async def update_agent(self, agent):
        self.agents[agent.id] = agent
        return agent

    async def create_card(self, card):
        card.id = card.id or "CARD-1"
        self.cards[card.id] = card
        return card

    async def get_card(self, card_id):
        return self.cards.get(card_id)


@pytest.mark.asyncio
async def test_orchestrator_initialize_enables_cache(monkeypatch):
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=True)

    fake_cache = CacheManager(db_path=":memory:")
    called = {}

    async def fake_init():
        called["init"] = True

    fake_cache.initialize = fake_init
    orch.cache = fake_cache

    await orch.initialize()
    assert called["init"] is True


def test_get_progress_zero_state():
    db = FakeDB()
    orch = AgentOrchestrator(db=db, llm_provider=MockLLMProvider(), enable_cache=False)
    progress = orch.get_progress()
    assert progress["percentage"] == 0
