import pytest
import pytest_asyncio

from eidolon.models import (
    Card,
    CardType,
    CardStatus,
    CardPriority,
    Agent,
    AgentScope,
    AgentStatus,
)
from eidolon.storage.database import Database


@pytest_asyncio.fixture()
async def db(tmp_path):
    database = Database(db_path=str(tmp_path / "eidolon.db"))
    await database.connect()
    try:
        yield database
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_card_crud_roundtrip(db: Database):
    card = Card(
        id="",
        type=CardType.REVIEW,
        title="Test Card",
        summary="Initial summary",
        priority=CardPriority.P1,
    )

    created = await db.create_card(card)
    assert created.id.startswith("Eidolon-")

    fetched = await db.get_card(created.id)
    assert fetched
    assert fetched.title == "Test Card"
    assert fetched.priority == CardPriority.P1
    assert fetched.status == CardStatus.NEW

    created.title = "Updated Title"
    created.update_status(CardStatus.PROPOSED, actor="tester")
    await db.update_card(created)

    updated = await db.get_card(created.id)
    assert updated.title == "Updated Title"
    assert updated.status == CardStatus.PROPOSED
    assert len(updated.log) >= 1


@pytest.mark.asyncio
async def test_agent_crud_and_status_tracking(db: Database):
    agent = Agent(
        id="",
        scope=AgentScope.FUNCTION,
        target="module.py::fn",
        status=AgentStatus.ANALYZING,
        parent_id=None,
        children_ids=[],
    )

    created = await db.create_agent(agent)
    assert created.id.startswith("AGN-FUN")

    fetched = await db.get_agent(created.id)
    assert fetched
    assert fetched.scope == AgentScope.FUNCTION
    assert fetched.status == AgentStatus.ANALYZING
    assert fetched.children_ids == []

    created.children_ids.append("child-1")
    created.update_status(AgentStatus.COMPLETED)
    await db.update_agent(created)

    updated = await db.get_agent(created.id)
    assert updated.children_ids == ["child-1"]
    assert updated.status == AgentStatus.COMPLETED
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_sequences_and_sessions(db: Database):
    # Sequence should increment for same card type
    card1 = await db.create_card(
        Card(id="", type=CardType.REVIEW, title="First", summary="")
    )
    card2 = await db.create_card(
        Card(id="", type=CardType.REVIEW, title="Second", summary="")
    )

    seq1 = int(card1.id.split("-")[-1])
    seq2 = int(card2.id.split("-")[-1])
    assert seq2 == seq1 + 1

    session_id = await db.create_analysis_session(
        session_id="sess-1",
        path="/tmp/project",
        mode="full",
        git_commit="abc123",
        git_branch="main",
    )

    await db.update_analysis_session(
        session_id=session_id,
        files_analyzed=["a.py"],
        files_skipped=[],
        total_modules=1,
        total_functions=2,
        cache_hits=0,
        cache_misses=0,
    )

    last_session = await db.get_last_analysis_session("/tmp/project")
    assert last_session
    assert last_session["id"] == "sess-1"
    assert last_session["git_commit"] == "abc123"
    assert last_session["files_analyzed"] == ["a.py"]
