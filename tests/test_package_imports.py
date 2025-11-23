def test_package_imports():
    import eidolon  # noqa: F401
    from eidolon import agents, analysis, code_graph  # noqa: F401

    assert hasattr(agents, "AgentOrchestrator")
    assert hasattr(code_graph, "CodeGraphAnalyzer")
