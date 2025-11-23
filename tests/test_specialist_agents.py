import json
import pytest

from eidolon.specialist_agents import (
    SpecialistRegistry,
    SpecialistDomain,
    SecurityEngineer,
    SpecialistReport,
    create_default_registry,
)
from eidolon.llm_providers.mock_provider import MockLLMProvider


def test_specialist_registry_lookup():
    provider = MockLLMProvider()
    registry = create_default_registry(provider)
    all_specs = registry.get_all_specialists()
    assert any(isinstance(s, SecurityEngineer) for s in all_specs)
    assert SpecialistDomain.SECURITY in registry.specialists


@pytest.mark.asyncio
async def test_security_engineer_analyze(monkeypatch):
    provider = MockLLMProvider()
    agent = SecurityEngineer(provider)

    async def fake_completion(messages, max_tokens=1024, temperature=0.0, **kwargs):
        from eidolon.llm_providers import LLMResponse
        content = """{
            "critical_issues": 1,
            "high_issues": 0,
            "medium_issues": 1,
            "low_issues": 0,
            "issues": [
                {"severity": "critical", "title": "SQL injection", "description": "unvalidated input"},
                {"severity": "medium", "title": "Missing rate limit", "description": "risk"}
            ],
            "recommendations": [
                {"severity": "critical", "title": "Use parameterized queries", "description": "fix"},
                {"severity": "medium", "title": "Add rate limiting", "description": "fix"}
            ]
        }"""
        return LLMResponse(content=content, input_tokens=0, output_tokens=0, model="mock")

    monkeypatch.setattr(provider, "create_completion", fake_completion)

    report = await agent.analyze("SELECT * FROM users where id = " + "user_input")
    assert isinstance(report, SpecialistReport)
    assert report.success is True
    assert report.critical_issues == 1
    assert report.medium_issues == 1
    assert len(report.recommendations) == 2
