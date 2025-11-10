from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

import yaml

from .compiler import RulepackCompiler
from .errors import RulepackError
from .loader import RulepackLoader
from .runtime import DEFAULT_DSN as RUNTIME_DEFAULT_DSN, evaluate_rulepack_file

DEFAULT_RULEPACK_FILENAME = "rulepack.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authoring helpers for the Eidolon Rulepack DSL")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_cmd = subcommands.add_parser("init", help="Create a starter rulepack.yaml in the current directory")
    init_cmd.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_RULEPACK_FILENAME),
        help="Destination file for the template pack (default: rulepack.yaml)",
    )
    init_cmd.add_argument("--force", action="store_true", help="Overwrite the file if it already exists")
    init_cmd.set_defaults(func=handle_init)

    test_cmd = subcommands.add_parser("test", help="Validate and compile a rulepack")
    test_cmd.add_argument("path", type=Path, help="Path to the rulepack YAML file")
    test_cmd.add_argument("--show-sql", action="store_true", help="Print compiled SQL for each rule")
    test_cmd.add_argument("--show-params", action="store_true", help="Print compiled parameter payloads")
    test_cmd.set_defaults(func=handle_test)

    publish_cmd = subcommands.add_parser("publish", help="Compile a rulepack and emit JSON artefact")
    publish_cmd.add_argument("path", type=Path, help="Path to the rulepack YAML file")
    publish_cmd.add_argument(
        "--output",
        type=Path,
        default=Path("compiled-rulepack.json"),
        help="Destination JSON file (default: compiled-rulepack.json)",
    )
    publish_cmd.add_argument("--force", action="store_true", help="Overwrite the destination file when it exists")
    publish_cmd.set_defaults(func=handle_publish)

    eval_cmd = subcommands.add_parser("eval", help="Execute a rulepack against a CodeGraph scan run")
    eval_cmd.add_argument("path", type=Path, help="Path to the rulepack YAML file")
    eval_cmd.add_argument("--run-id", type=int, required=True, help="scan_runs.id to evaluate")
    eval_cmd.add_argument(
        "--dsn",
        default=RUNTIME_DEFAULT_DSN,
        help=f"Postgres DSN hosting CodeGraph tables (default: {RUNTIME_DEFAULT_DSN})",
    )
    eval_cmd.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to write the evaluation report (defaults to stdout)",
    )
    eval_cmd.set_defaults(func=handle_eval)

    return parser


def handle_init(args: argparse.Namespace) -> int:
    output_path: Path = args.output
    if output_path.exists() and not args.force:
        raise RulepackError(f"{output_path} already exists. Re-run with --force to overwrite.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_sample_pack(), encoding="utf-8")
    print(f"Wrote template rulepack to {output_path}")
    return 0


def handle_test(args: argparse.Namespace) -> int:
    loader = RulepackLoader()
    compiler = RulepackCompiler()
    pack = loader.load(args.path)
    compiled = compiler.compile(pack)
    print(f"{pack.metadata.id} v{pack.metadata.version}: {len(compiled.rules)} rule(s) validated")
    if args.show_sql:
        for rule in compiled.rules:
            print(f"- {rule.id} ({rule.selector_source})")
            print(textwrap.indent(rule.sql, "    "))
            if args.show_params and rule.parameters:
                params = json.dumps(rule.parameters, indent=2)
                print(textwrap.indent(params, "    "))
    elif args.show_params:
        for rule in compiled.rules:
            print(f"- {rule.id}")
            if rule.parameters:
                params = json.dumps(rule.parameters, indent=2)
                print(textwrap.indent(params, "    "))
            else:
                print("    (no parameters)")
    return 0


def handle_publish(args: argparse.Namespace) -> int:
    loader = RulepackLoader()
    compiler = RulepackCompiler()
    pack = loader.load(args.path)
    compiled = compiler.compile(pack)
    output_path: Path = args.output
    if output_path.exists() and not args.force:
        raise RulepackError(f"{output_path} already exists. Re-run with --force to overwrite.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = compiled.to_dict()
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Compiled {pack.metadata.id} → {output_path}")
    return 0


def handle_eval(args: argparse.Namespace) -> int:
    report = evaluate_rulepack_file(args.path, run_id=args.run_id, dsn=args.dsn)
    payload = report.to_dict()
    json_payload = json.dumps(payload, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json_payload, encoding="utf-8")
        print(f"Wrote evaluation report to {args.output}")
    else:
        print(json_payload)
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        exit_code = args.func(args)
    except RulepackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover
        print(f"unexpected error: {exc}", file=sys.stderr)
        raise
    raise SystemExit(exit_code)


def _render_sample_pack() -> str:
    sample = {
        "metadata": {
            "id": "RP-LOCAL-DEMO",
            "name": "Local Demo Pack",
            "version": "0.1.0",
            "summary": "Sample layering + call guardrails.",
            "owners": ["refiner", "conformance"],
            "tags": ["demo", "rulepack"],
        },
        "rules": [
            {
                "id": "layering-app-blocks-data",
                "description": "App layer boundaries cannot import data layer modules.",
                "category": "layering",
                "severity": "error",
                "enforcement": "block",
                "scopes": ["drift", "gatecheck"],
                "selector": {
                    "source": "import_edges",
                    "conditions": [
                        {"field": "source_boundary", "op": "match", "value": "app.*"},
                        {"field": "target_name", "op": "match", "value": "data.*"},
                    ],
                },
                "predicate": {"kind": "forbid"},
                "autofix": {
                    "action": "introduce_facade",
                    "message": "Route data access through an app service facade.",
                },
            },
            {
                "id": "security-no-unsafe-calls",
                "description": "Avoid invoking eval/exec to keep plans deterministic.",
                "category": "security",
                "severity": "warn",
                "enforcement": "warn",
                "scopes": ["drift", "gatecheck"],
                "selector": {
                    "source": "function_calls",
                    "conditions": [{"field": "callee_name", "op": "in", "value": ["eval", "exec"]}],
                },
                "predicate": {"kind": "forbid"},
            },
        ],
    }
    return yaml.safe_dump(sample, sort_keys=False)


if __name__ == "__main__":  # pragma: no cover
    main()
