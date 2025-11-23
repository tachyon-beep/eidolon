from pathlib import Path

from eidolon.design_context_tools import DesignContextToolHandler
from eidolon.code_graph import CodeGraph, CodeElement, CodeElementType


def build_design_graph(tmp_path: Path) -> CodeGraph:
    graph = CodeGraph(project_path=tmp_path)
    mod_path = tmp_path / "subsys" / "mod.py"
    mod_path.parent.mkdir(parents=True, exist_ok=True)
    mod_path.write_text("# sample\n")

    module = CodeElement(
        id="subsys.mod",
        name="mod",
        type=CodeElementType.MODULE,
        file_path=mod_path,
        line_number=1,
        source_code="",
        imports=["os", "sys"],
        docstring="auth module",
        parent_subsystem="subsys",
        lines_of_code=1,
    )
    cls = CodeElement(
        id="subsys.mod::Controller",
        name="Controller",
        type=CodeElementType.CLASS,
        file_path=mod_path,
        line_number=1,
        source_code="class Controller: ...",
        parent_module="subsys.mod",
        parent_subsystem="subsys",
        lines_of_code=1,
    )
    func = CodeElement(
        id="subsys.mod::login",
        name="login",
        type=CodeElementType.FUNCTION,
        file_path=mod_path,
        line_number=2,
        source_code="def login(): ...",
        parent_module="subsys.mod",
        parent_subsystem="subsys",
        lines_of_code=1,
    )

    for elem in (module, cls, func):
        graph.elements[elem.id] = elem
    graph.modules[module.id] = module
    graph.classes[cls.id] = cls
    graph.functions[func.id] = func
    return graph


def test_get_existing_and_pattern_analysis(tmp_path):
    graph = build_design_graph(tmp_path)
    handler = DesignContextToolHandler(code_graph=graph)

    existing = handler.handle_tool_call("get_existing_modules", {"subsystem": "subsys"})
    assert existing["found"] is True
    assert existing["count"] == 1
    assert existing["modules"][0]["functions"] == 1
    assert existing["modules"][0]["classes"] == 1

    pattern = handler.handle_tool_call("analyze_module_pattern", {"module_name": "mod"})
    assert pattern["found"] is True
    assert pattern["pattern"] in {"MVC", "Object-Oriented", "Procedural", "Layered Architecture"}


def test_search_and_subsystem_overview(tmp_path):
    graph = build_design_graph(tmp_path)
    handler = DesignContextToolHandler(code_graph=graph)

    search = handler.handle_tool_call("search_similar_modules", {"responsibility": "auth"})
    assert search["found"] is True
    assert search["count"] >= 1

    overview = handler.handle_tool_call("get_subsystem_architecture", {"subsystem_name": "subsys"})
    assert overview["found"] is True
    assert overview["module_count"] == 1
    assert overview["total_classes"] == 1
    assert overview["total_functions"] == 1


def test_propose_and_validate(tmp_path):
    graph = build_design_graph(tmp_path)
    handler = DesignContextToolHandler(
        code_graph=graph,
        design_constraints={"db": "must use sqlite"},
    )

    proposal = handler.handle_tool_call(
        "propose_design_option",
        {
            "option_name": "Option A",
            "structure": {"modules": ["auth"]},
            "rationale": "Use simple design to start",
        },
    )
    assert proposal["accepted"] is True
    assert handler.proposed_designs

    clarification = handler.handle_tool_call(
        "request_requirement_clarification",
        {
            "question": "Which DB?",
            "context": "Need to pick datastore",
            "options": ["sqlite", "postgres"],
        },
    )
    assert "clarification" in clarification
    assert clarification.get("recommendation") in ["sqlite", "postgres"]

    constraints = handler.handle_tool_call(
        "get_dependency_constraints",
        {"scope": "module"},
    )
    assert constraints["constraints"]

    validation = handler.handle_tool_call(
        "validate_design_decision",
        {"decision": "Use sqlite", "context": "Local dev"},
    )
    assert validation["valid"] is True


def test_unknown_tool_and_no_graph():
    handler = DesignContextToolHandler(code_graph=None)
    result = handler.handle_tool_call("get_existing_modules", {})
    assert result["found"] is False

    unknown = handler.handle_tool_call("nope", {})
    assert "error" in unknown
