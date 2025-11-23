import pytest

from eidolon.code_context_tools import CodeContextToolHandler
from eidolon.code_graph import CodeGraph, CodeElement, CodeElementType


def build_graph(tmp_path):
    graph = CodeGraph(project_path=tmp_path)

    mod_path = tmp_path / "mod.py"
    mod_path.write_text(
        """
def helper():
    return 1


def main():
    return helper()
"""
    )

    module = CodeElement(
        id="mod",
        name="mod",
        type=CodeElementType.MODULE,
        file_path=mod_path,
        line_number=1,
        source_code=mod_path.read_text(),
        imports=[],
        lines_of_code=4,
        parent_subsystem="root",
    )
    helper = CodeElement(
        id="mod::helper",
        name="helper",
        type=CodeElementType.FUNCTION,
        file_path=mod_path,
        line_number=1,
        source_code="def helper():\n    return 1\n",
        signature="helper()",
        calls=[],
        called_by=["mod::main"],
        parent_module="mod",
        parent_subsystem="root",
        lines_of_code=2,
    )
    main = CodeElement(
        id="mod::main",
        name="main",
        type=CodeElementType.FUNCTION,
        file_path=mod_path,
        line_number=4,
        source_code="def main():\n    return helper()\n",
        signature="main()",
        calls=["helper"],
        called_by=[],
        parent_module="mod",
        parent_subsystem="root",
        lines_of_code=2,
    )

    graph.modules[module.id] = module
    graph.elements[module.id] = module
    for func in (helper, main):
        graph.functions[func.id] = func
        graph.elements[func.id] = func

    return graph


def test_get_function_definition(tmp_path):
    graph = build_graph(tmp_path)
    handler = CodeContextToolHandler(code_graph=graph)

    result = handler.handle_tool_call(
        "get_function_definition",
        {"function_name": "helper"},
    )

    assert result["found"] is True
    assert result["function_name"] == "helper"
    assert "source_code" in result


def test_get_callers_and_callees(tmp_path):
    graph = build_graph(tmp_path)
    handler = CodeContextToolHandler(code_graph=graph)

    callers = handler.handle_tool_call("get_function_callers", {"function_name": "helper"})
    assert callers["caller_count"] == 1
    assert callers["callers"][0]["name"] == "main"

    callees = handler.handle_tool_call("get_function_callees", {"function_name": "main"})
    assert callees["callee_count"] == 1
    assert callees["callees"][0]["name"] == "helper"


def test_module_overview_and_search(tmp_path):
    graph = build_graph(tmp_path)
    handler = CodeContextToolHandler(code_graph=graph)

    overview = handler.handle_tool_call(
        "get_module_overview",
        {"module_path": "mod.py", "include_source": True},
    )
    assert overview["found"] is True
    assert overview["function_count"] == 2
    assert overview["class_count"] == 0
    assert overview["functions"][0]["name"] in {"helper", "main"}

    search = handler.handle_tool_call("search_functions", {"pattern": "main", "limit": 5})
    assert search["match_count"] == 1
    assert search["matches"][0]["name"] == "main"


def test_unknown_tool_and_missing_graph():
    handler = CodeContextToolHandler(code_graph=None)
    missing = handler.handle_tool_call("get_function_definition", {"function_name": "x"})
    assert "error" in missing

    handler = CodeContextToolHandler(code_graph=CodeGraph(project_path=None))
    unknown = handler.handle_tool_call("nope", {})
    assert "error" in unknown
