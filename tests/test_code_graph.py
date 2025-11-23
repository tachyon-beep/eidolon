import pytest

from eidolon.code_graph import CodeGraphAnalyzer


@pytest.mark.asyncio
async def test_code_graph_builds_call_graph(tmp_path):
    module = tmp_path / "app.py"
    module.write_text(
        """
def helper(x):
    return x + 1


def main(y):
    return helper(y) * 2
"""
    )

    analyzer = CodeGraphAnalyzer()
    graph = await analyzer.analyze_project(tmp_path)

    assert graph.total_modules == 1
    assert graph.total_functions == 2
    assert graph.call_graph.has_edge("app::main", "app::helper")
