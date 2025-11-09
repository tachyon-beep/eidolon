from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two scanner record files to detect renames/additions")
    parser.add_argument("before", type=Path, help="JSONL records from baseline scan")
    parser.add_argument("after", type=Path, help="JSONL records from follow-up scan")
    parser.add_argument("--output", type=Path, help="Optional path to write comparison JSON")
    return parser.parse_args()


def load_map(path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            mapping[record["sha256"]] = record["path"]
    return mapping


def compare(before: Dict[str, str], after: Dict[str, str]) -> dict:
    unchanged = sum(1 for sha, path in before.items() if after.get(sha) == path)
    renamed = sum(1 for sha, path in before.items() if sha in after and after[sha] != path)
    removed = sum(1 for sha in before if sha not in after)
    added = sum(1 for sha in after if sha not in before)
    return {
        "total_before": len(before),
        "total_after": len(after),
        "unchanged": unchanged,
        "renamed": renamed,
        "removed": removed,
        "added": added,
    }


def main() -> None:
    args = parse_args()
    before = load_map(args.before.resolve())
    after = load_map(args.after.resolve())
    summary = compare(before, after)
    summary_json = json.dumps(summary, indent=2)
    if args.output:
        args.output.write_text(summary_json, encoding="utf-8")
    else:
        print(summary_json)


if __name__ == "__main__":  # pragma: no cover
    main()
