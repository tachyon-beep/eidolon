import asyncio
import os

import pytest

from eidolon.llm_providers import OpenAICompatibleProvider
from eidolon.utils.json_utils import extract_json_from_response


_llm_skip = pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
    reason="LLM key not configured",
)


@pytest.mark.integration
@pytest.mark.llm
@_llm_skip
def test_llm_structured_output():
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # use OpenAI model on OpenRouter

    provider = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)

    async def run():
        resp = await provider.create_completion(
            messages=[{"role": "user", "content": "Return a JSON object with fields {foo:str, bar:int}"}],
            max_tokens=64,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        parsed = extract_json_from_response(resp.content)
        assert isinstance(parsed, dict)
        assert "foo" in parsed and "bar" in parsed

    asyncio.run(run())
