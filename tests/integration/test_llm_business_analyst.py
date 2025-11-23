import asyncio
import os
from pathlib import Path

import pytest

from eidolon.business_analyst import BusinessAnalyst
from eidolon.llm_providers import OpenAICompatibleProvider
from eidolon.code_graph import CodeGraphAnalyzer
from eidolon.design_context_tools import DesignContextToolHandler


_llm_skip = pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
    reason="LLM key not configured",
)


@pytest.mark.integration
@pytest.mark.llm
@_llm_skip
def test_llm_business_analyst(tmp_path):
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    provider = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)

    # Tiny project context
    sample = tmp_path / "demo.py"
    sample.write_text("def hello(name: str) -> str:\n    return f'hi {name}'\n")

    async def run():
        graph = await CodeGraphAnalyzer().analyze_project(tmp_path)
        design_tools = DesignContextToolHandler(code_graph=graph)
        ba = BusinessAnalyst(llm_provider=provider, code_graph=graph, design_tool_handler=design_tools)

        result = await ba.analyze_request("Add greeting endpoint", str(tmp_path))
        assert result.change_type
        assert result.affected_subsystems is not None
        assert result.refined_requirements

    asyncio.run(run())
