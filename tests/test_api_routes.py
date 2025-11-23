import types
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from eidolon.api.routes import create_routes
from eidolon.models import Card, CardType, CardStatus


class FakeDB:
    def __init__(self):
        self.cards = {}

    async def get_all_cards(self, filters=None):
        return list(self.cards.values())

    async def get_card(self, card_id: str):
        return self.cards.get(card_id)

    async def create_card(self, card: Card):
        self.cards[card.id] = card
        return card

    async def update_card(self, card: Card):
        self.cards[card.id] = card
        return card


class FakeOrchestrator:
    def __init__(self):
        self.analyzed_paths = []
        self.incremental_calls = []
        self.activity_callback = None

    async def analyze_codebase(self, path: str):
        self.analyzed_paths.append(path)
        return type("AgentObj", (), {"id": "agent-123"})

    async def analyze_incremental(self, path: str, base=None):
        self.incremental_calls.append((path, base))
        return {
            "status": "completed",
            "session_id": "sess-1",
            "stats": {"files_analyzed": 1},
            "git_info": {},
            "hierarchy": {},
        }

    async def get_agent_hierarchy(self, root_agent_id: str):
        return {"id": root_agent_id, "children": []}

    def get_progress(self):
        return {"percentage": 0}

    def set_activity_callback(self, callback):
        self.activity_callback = callback


class FakeAnalysisContext:
    def __init__(self):
        self.id = "agent-123"
        self.children_ids = []
        self.findings = []
        self.cards_created = []

    def dict(self):
        return {"id": self.id}


def setup_app():
    app = FastAPI()
    db = FakeDB()
    orchestrator = FakeOrchestrator()
    router = create_routes(db, orchestrator)
    app.include_router(router, prefix="/api")
    return app, db, orchestrator


def test_card_endpoints_basic():
    app, db, _ = setup_app()
    client = TestClient(app)

    # Pre-seed a card
    card = Card(
        id="eidolon-2025-REV-0001",
        type=CardType.REVIEW,
        title="t",
        summary="s",
        status=CardStatus.NEW,
        priority="P1",
    )
    import anyio

    anyio.run(db.create_card, card)

    res = client.get("/api/cards")
    assert res.status_code == 200
    assert res.json()[0]["id"] == card.id

    res_one = client.get(f"/api/cards/{card.id}")
    assert res_one.status_code == 200

    res_missing = client.get("/api/cards/doesnotexist")
    assert res_missing.status_code == 404


def test_analyze_routes():
    app, _, orchestrator = setup_app()
    client = TestClient(app)

    path = str(Path.cwd())
    res = client.post("/api/analyze", json={"path": path})
    assert res.status_code == 200
    data = res.json()
    assert data["agent_id"] == "agent-123"

    res_inc = client.post("/api/analyze/incremental", json={"path": path, "base": "HEAD"})
    assert res_inc.status_code == 200
    inc_data = res_inc.json()
    assert inc_data["session_id"] == "sess-1"
