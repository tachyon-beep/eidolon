from __future__ import annotations

import argparse
import random
import textwrap
from pathlib import Path

DEFAULT_PACKAGES = 5
DEFAULT_MODULES = 20
DEFAULT_CLASSES = 5
DEFAULT_FUNCTIONS = 10
DEFAULT_SLOC_PADDING = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic Python repo for scanner benchmarks")
    parser.add_argument("output", type=Path, help="Directory to generate the synthetic repo into")
    parser.add_argument("--packages", type=int, default=DEFAULT_PACKAGES)
    parser.add_argument("--modules", type=int, default=DEFAULT_MODULES)
    parser.add_argument("--classes", type=int, default=DEFAULT_CLASSES)
    parser.add_argument("--functions", type=int, default=DEFAULT_FUNCTIONS)
    parser.add_argument("--padding", type=int, default=DEFAULT_SLOC_PADDING, help="Extra docstring lines per class/function")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    for pkg_idx in range(args.packages):
        pkg_dir = output / f"pkg_{pkg_idx:03d}"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text("\n", encoding="utf-8")
        for mod_idx in range(args.modules):
            module_name = f"module_{mod_idx:03d}.py"
            module_path = pkg_dir / module_name
            module_path.write_text(render_module(pkg_idx, mod_idx, args), encoding="utf-8")


def render_module(pkg_idx: int, mod_idx: int, args: argparse.Namespace) -> str:
    header = [
        "\"\"\"Synthetic module for benchmark\"\"\"",
        "import math",
        "import random",
        "",
    ]
    body: list[str] = []
    for cls_idx in range(args.classes):
        body.append(render_class(pkg_idx, mod_idx, cls_idx, args))
    for fn_idx in range(args.functions):
        body.append(render_function(pkg_idx, mod_idx, fn_idx, args))
    return "\n".join(header + body)


def render_class(pkg_idx: int, mod_idx: int, cls_idx: int, args: argparse.Namespace) -> str:
    name = f"Pkg{pkg_idx}Mod{mod_idx}Class{cls_idx}"
    doc = "\n".join(f"Line {i} of class docstring." for i in range(args.padding))
    method_blocks: list[str] = []
    for m_idx in range(3):
        method_block = textwrap.dedent(
            f"""
            def method_{m_idx}(self, x: float) -> float:
                \"\"\"Method {m_idx} performing simple math.\"\"\"
                total = 0.0
                for i in range({args.padding}):
                    total += (x + i) * math.cos(i)
                return total
            """
        ).strip()
        method_blocks.append(textwrap.indent(method_block, "    "))
    methods_text = "\n\n".join(method_blocks)
    doc_indented = textwrap.indent(doc, " " * 4)
    class_block = textwrap.dedent(
        f"""
        class {name}:
            \"\"\"
{doc_indented}
            \"\"\"
            CONST = {pkg_idx * 100 + mod_idx * 10 + cls_idx}

            def __init__(self, seed: int = 0):
                self.rng = random.Random(seed)

{methods_text}
        """
    ).strip()
    return class_block + "\n\n"


def render_function(pkg_idx: int, mod_idx: int, fn_idx: int, args: argparse.Namespace) -> str:
    name = f"pkg{pkg_idx}_mod{mod_idx}_fn{fn_idx}"
    doc = "\n".join(f"Function doc line {i}." for i in range(args.padding))
    return textwrap.dedent(
        f"""
        def {name}(items: list[float]) -> float:
            \"\"\"{doc}\"\"\"
            total = 0.0
            for idx, item in enumerate(items):
                total += item * math.sin(idx)
            bias = {pkg_idx + mod_idx + fn_idx}
            return total + bias
        """
    ).strip() + "\n\n"


if __name__ == "__main__":  # pragma: no cover
    main()
