from eidolon.analysis import CodeAnalyzer


def test_analyze_file_extracts_functions_and_classes(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        """
import math


def add(a, b):
    return a + b


class Greeter:
    def hello(self, name: str):
        return f"Hi {name}"
"""
    )

    analyzer = CodeAnalyzer(base_path=tmp_path)
    module = analyzer.analyze_file(str(sample))

    assert [f.name for f in module.functions] == ["add"]
    assert [c.name for c in module.classes] == ["Greeter"]

    smells = analyzer.detect_code_smells(module)
    smell_types = {s["type"] for s in smells}
    assert "missing_docstring" in smell_types
