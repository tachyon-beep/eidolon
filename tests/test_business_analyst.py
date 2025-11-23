import json
import pytest

from eidolon.business_analyst import BusinessAnalyst, RequirementsAnalysis
from eidolon.llm_providers.mock_provider import MockLLMProvider
from eidolon.code_graph import CodeGraph
from eidolon.design_context_tools import DesignContextToolHandler


@pytest.mark.asyncio
async def test_business_analyst_parses_requirements(monkeypatch, tmp_path):
    provider = MockLLMProvider()
    graph = CodeGraph(project_path=tmp_path)
    design_tools = DesignContextToolHandler(code_graph=graph)
    ba = BusinessAnalyst(llm_provider=provider, code_graph=graph, design_tool_handler=design_tools)

    expected = {
        "change_type": "feature",
        "complexity_estimate": "medium",
        "affected_subsystems": ["api"],
        "refined_requirements": "Do X",
        "analysis_turns": 1,
        "tools_used": [],
        "clear_objectives": ["objective"],
    }

    async def fake_completion(messages, max_tokens=2048, temperature=0.0, tools=None, tool_choice=None, **kwargs):
        from eidolon.llm_providers import LLMResponse
        return LLMResponse(content=json.dumps(expected), input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    result = await ba.analyze_request("Add auth", str(tmp_path))
    assert isinstance(result, RequirementsAnalysis)
    assert result.change_type == "feature"
    assert result.complexity_estimate == "medium"
    assert result.affected_subsystems == ["api"]
    assert result.refined_requirements == "Do X"
