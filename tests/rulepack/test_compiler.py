from __future__ import annotations

from pathlib import Path

from eidolon.rulepack.compiler import RulepackCompiler
from eidolon.rulepack.loader import RulepackLoader

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rulepacks" / "sample.yaml"


def test_compiler_generates_sql_fragments() -> None:
    pack = RulepackLoader().load(FIXTURE)
    compiled = RulepackCompiler().compile(pack)

    layering = compiled.rules[0]
    assert layering.selector_source == "import_edges"
    assert layering.sql.splitlines() == [
        "SELECT ie.source_boundary AS source_boundary, ie.target_name AS target_name, ie.usage_count AS usage_count",
        "FROM import_edges AS ie",
        "WHERE ie.run_id = %(run_id)s",
        "  AND (ie.source_boundary LIKE %(source_boundary_0)s ESCAPE '\\\\')",
        "  AND (ie.target_name LIKE %(target_name_1)s ESCAPE '\\\\')",
    ]
    assert layering.parameters == {"source_boundary_0": "app.%", "target_name_1": "data.%"}

    calls = compiled.rules[1]
    assert calls.sql.splitlines() == [
        "SELECT fc.path AS path, fc.callee_name AS callee_name",
        "FROM function_calls AS fc",
        "WHERE fc.run_id = %(run_id)s",
        "  AND fc.callee_name = ANY(%(callee_name_0)s)",
    ]
    assert calls.parameters == {"callee_name_0": ["eval", "exec"]}
