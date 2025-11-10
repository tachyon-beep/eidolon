from __future__ import annotations

from pathlib import Path

import pytest

from eidolon.rulepack.loader import RulepackLoader
from eidolon.rulepack.compiler import RulepackCompiler


CATALOG_DIR = Path("rulepacks")
PACK_PATHS = sorted(CATALOG_DIR.glob("*/rulepack.yaml"))


@pytest.mark.parametrize("pack_path", PACK_PATHS)
def test_catalog_rulepacks_compile(pack_path: Path) -> None:
    loader = RulepackLoader()
    compiler = RulepackCompiler()
    pack = loader.load(pack_path)
    compiled = compiler.compile(pack)
    assert compiled.rules, f"Expected rules in {pack_path}"
