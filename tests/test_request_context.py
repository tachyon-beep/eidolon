import asyncio
import pytest

from eidolon.request_context import AnalysisRegistry, AnalysisCancelledError, cancellable


@pytest.mark.asyncio
async def test_analysis_registry_create_cancel_remove():
    registry = AnalysisRegistry()
    ctx = await registry.create(path="/repo", mode="full")
    assert ctx.session_id
    assert registry.count_active() == 1

    fetched = await registry.get(ctx.session_id)
    assert fetched is ctx

    cancelled = await registry.cancel(ctx.session_id, reason="stop")
    assert cancelled is True
    assert ctx.is_cancelled()

    await registry.remove(ctx.session_id)
    assert registry.count_active() == 0


@pytest.mark.asyncio
async def test_cancel_all_and_status():
    registry = AnalysisRegistry()
    ctx1 = await registry.create(path="/a", mode="full")
    ctx2 = await registry.create(path="/b", mode="incremental")

    statuses = await registry.get_all_active()
    assert ctx1.session_id in statuses and ctx2.session_id in statuses

    await registry.cancel_all(reason="shutdown")
    assert ctx1.is_cancelled() and ctx2.is_cancelled()


@pytest.mark.asyncio
async def test_cancellable_decorator():
    registry = AnalysisRegistry()
    ctx = await registry.create(path="/repo", mode="full")

    @cancellable
    async def work(context: ctx.__class__):
        await context.check_cancelled()
        return "done"

    result = await work(ctx)
    assert result == "done"

    ctx.cancel("stop")

    with pytest.raises(AnalysisCancelledError):
        await work(ctx)
