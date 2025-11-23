import json
import pytest

from eidolon.planning.review_loop import ReviewLoop, ReviewDecision
from eidolon.llm_providers.mock_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_review_loop_accepts_on_good_score(monkeypatch):
    provider = MockLLMProvider()
    loop = ReviewLoop(llm_provider=provider)

    async def fake_completion(messages, max_tokens=1024, temperature=0.0, **kwargs):
        from eidolon.llm_providers import LLMResponse
        content = json.dumps(
            {
                "decision": "accept",
                "score": 90,
                "issues": [],
                "strengths": ["good"],
                "suggestions": [],
                "reasoning": "ok",
            }
        )
        return LLMResponse(content=content, input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    result = await loop.review_and_revise(
        initial_output={"plan": 1},
        primary_agent_func=None,
        review_context={"tier": "system", "type": "plan"},
        min_score=75,
        max_iterations=2,
    )

    assert isinstance(result, dict)
    meta = result.get("_review_metadata")
    assert meta["final_decision"] == "accept"
    assert meta["iterations"] == 1


@pytest.mark.asyncio
async def test_review_loop_revision_and_reject(monkeypatch):
    provider = MockLLMProvider()
    loop = ReviewLoop(llm_provider=provider)

    decisions = iter(
        [
            {"decision": "revise_minor", "score": 50},
            {"decision": "reject", "score": 40},
        ]
    )

    async def fake_completion(messages, max_tokens=1024, temperature=0.0, **kwargs):
        from eidolon.llm_providers import LLMResponse
        decision = next(decisions)
        content = json.dumps(
            {
                "decision": decision["decision"],
                "score": decision["score"],
                "issues": ["issue"],
                "strengths": [],
                "suggestions": ["fix it"],
                "reasoning": "needs work",
            }
        )
        return LLMResponse(content=content, input_tokens=0, output_tokens=0, model="mock")

    async def primary_agent_func(**kwargs):
        return {"plan": "revised"}

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    result = await loop.review_and_revise(
        initial_output={"plan": "initial"},
        primary_agent_func=primary_agent_func,
        review_context={"tier": "system", "type": "plan"},
        min_score=80,
        max_iterations=3,
    )

    meta = result.get("_review_metadata")
    assert meta["final_decision"] == "reject"
    assert meta["iterations"] == 2
    assert meta["failed"] is True
