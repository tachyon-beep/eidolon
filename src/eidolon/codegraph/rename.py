from __future__ import annotations

import argparse
import random
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename/move a subset of synthetic modules to simulate drift")
    parser.add_argument("root", type=Path, help="Synthetic repo root")
    parser.add_argument("--count", type=int, default=1000, help="Number of modules to move")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    random.seed(args.seed)
    modules = sorted(root.glob("pkg_*/module_*.py"))
    if len(modules) < args.count:
        raise SystemExit(f"Requested {args.count} modules but only {len(modules)} available")
    selected = random.sample(modules, args.count)
    for path in selected:
        pkg_dir = path.parent
        new_pkg_dir = pkg_dir.parent / f"{pkg_dir.name}_moved"
        new_pkg_dir.mkdir(parents=True, exist_ok=True)
        new_name = path.stem + "_moved.py"
        new_path = new_pkg_dir / new_name
        counter = 1
        while new_path.exists():
            new_path = new_pkg_dir / f"{path.stem}_moved_{counter}.py"
            counter += 1
        path.rename(new_path)
    print(f"Moved {len(selected)} modules into *_moved packages under {root}")


if __name__ == "__main__":  # pragma: no cover
    main()
