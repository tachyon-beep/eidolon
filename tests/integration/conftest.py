import os
import pytest


def have_llm_key():
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))


llm_required = pytest.mark.skipif(
    not have_llm_key(),
    reason="LLM key not configured (OPENAI_API_KEY or OPENROUTER_API_KEY)",
)


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: integration test")
    config.addinivalue_line("markers", "llm: requires live LLM API key")
