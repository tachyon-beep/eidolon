import os
import pytest

from eidolon.llm_providers import (
    create_provider,
    get_provider_info,
    LLMResponse,
)
from eidolon.llm_providers.mock_provider import MockLLMProvider


def test_create_provider_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    provider = create_provider()
    assert isinstance(provider, MockLLMProvider)
    assert provider.get_provider_name() == "mock"
    assert provider.get_model_name() == "mock-gpt-4"


def test_get_provider_info(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    info = get_provider_info()
    assert info["provider"] == "anthropic"
    assert info["configured"] is False
    assert "model" in info

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-x")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")

    info = get_provider_info()
    assert info["provider"] == "openai"
    assert info["configured"] is True
    assert info["model"] == "gpt-x"
    assert info["base_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_mock_provider_completion():
    provider = MockLLMProvider()
    response: LLMResponse = await provider.create_completion(
        messages=[{"role": "user", "content": "You are analyzing a function"}],
        max_tokens=128,
    )
    assert response.content
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert provider.call_count == 1
