import pytest

from eidolon.planning.agent_selector import IntelligentAgentSelector, AgentTier
from eidolon.planning.prompt_templates import AgentRole
from eidolon.llm_providers.mock_provider import MockLLMProvider


def test_select_agent_heuristic_design_default():
    selector = IntelligentAgentSelector()
    result = selector.select_agent_heuristic("Please add a new login feature")
    assert result["role"] == AgentRole.DESIGN
    assert result["tier"] == AgentTier.SYSTEM
    assert result["confidence"] > 0


def test_select_agent_heuristic_testing_keyword():
    selector = IntelligentAgentSelector()
    result = selector.select_agent_heuristic("Write pytest tests for the API")
    assert result["role"] == AgentRole.TESTING
    assert result["tier"] == AgentTier.MODULE


@pytest.mark.asyncio
async def test_select_agent_llm_mock(monkeypatch):
    selector = IntelligentAgentSelector(llm_provider=MockLLMProvider())

    # Force deterministic mock response by overriding create_completion
    async def fake_completion(messages, max_tokens=1024, temperature=0.0, **kwargs):
        content = """{
            "role": "implementation",
            "tier": "function",
            "confidence": 0.9,
            "reasoning": "Explicit code generation request"
        }"""
        from eidolon.llm_providers import LLMResponse

        return LLMResponse(
            content=content,
            input_tokens=0,
            output_tokens=0,
            model="mock",
        )

    monkeypatch.setattr(selector.llm_provider, "create_completion", fake_completion)

    result = await selector.select_agent_llm("Implement a function to hash passwords")
    assert result["role"] == AgentRole.IMPLEMENTATION
    assert result["tier"] == AgentTier.FUNCTION
    assert result["confidence"] >= 0.8
