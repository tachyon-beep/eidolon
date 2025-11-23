import asyncio
import os
from pathlib import Path

import pytest

from eidolon.agents.orchestrator import AgentOrchestrator
from eidolon.llm_providers import OpenAICompatibleProvider
from eidolon.storage.database import Database


_llm_skip = pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
    reason="LLM key not configured",
)


@pytest.mark.integration
@pytest.mark.llm
@_llm_skip
def test_llm_single_function_analysis(tmp_path):
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    provider = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)

    # Tiny project
    mod = tmp_path / "demo.py"
    mod.write_text(
        """
import math

def hypot(a: float, b: float) -> float:
    return math.sqrt(a*a + b*b)
"""
    )

    async def run():
        db = Database(db_path=str(tmp_path / "demo.db"))
        await db.connect()

        orch = AgentOrchestrator(
            db=db,
            llm_provider=provider,
            enable_cache=False,
            max_concurrent_modules=1,
            max_concurrent_functions=1,
        )
        await orch.initialize()

        system_agent = await orch.analyze_codebase(str(tmp_path))
        assert system_agent.cards_created

        hierarchy = await orch.get_agent_hierarchy(system_agent.id)
        assert hierarchy["children"]

        await db.close()

    asyncio.run(run())
