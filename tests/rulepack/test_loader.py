from __future__ import annotations

from pathlib import Path

import pytest

from eidolon.rulepack.errors import RulepackSchemaError
from eidolon.rulepack.loader import RulepackLoader

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rulepacks"


def test_loader_reads_fixture() -> None:
    loader = RulepackLoader()
    pack = loader.load(FIXTURES / "sample.yaml")
    assert pack.metadata.id == "RP-SAMPLE"
    assert len(pack.rules) == 2
    assert pack.rules[0].selector.source == "import_edges"
    assert pack.rules[1].selector.source == "function_calls"


def test_loader_rejects_invalid_schema(tmp_path: Path) -> None:
    invalid_pack = tmp_path / "invalid.yaml"
    invalid_pack.write_text(
        "\n".join(
            [
                "metadata:",
                "  name: Missing Fields",
                "  version: 0.0.1",
                "  summary: invalid pack",
                "  owners: []",
            ]
        ),
        encoding="utf-8",
    )
    loader = RulepackLoader()
    with pytest.raises(RulepackSchemaError) as exc:
        loader.load(invalid_pack)
    assert "metadata.owners" in str(exc.value)
