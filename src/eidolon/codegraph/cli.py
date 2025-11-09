from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .scanner import CodeGraphScanner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototype CodeGraph scanner benchmark")
    parser.add_argument("repo", type=Path, help="Path to repository root to scan")
    parser.add_argument(
        "--records",
        type=Path,
        default=None,
        help="Optional path to write per-file metrics as JSON Lines",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional path to write the summary JSON report",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symlinks when searching for Python files",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=None,
        help="Additional directory names to exclude (e.g. build temp folders)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    scanner = CodeGraphScanner(
        repo,
        exclude_dirs=args.exclude,
        follow_symlinks=args.follow_symlinks,
    )
    records_path: Optional[Path] = args.records.resolve() if args.records else None
    if records_path:
        records_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path: Optional[Path] = args.summary.resolve() if args.summary else None
    if summary_path:
        summary_path.parent.mkdir(parents=True, exist_ok=True)

    report = scanner.scan(records_path=records_path)

    if summary_path:
        summary_path.write_text(report.to_json(), encoding="utf-8")
    else:
        print(report.to_json())


if __name__ == "__main__":  # pragma: no cover
    main()
