from __future__ import annotations

import argparse
import json
from pathlib import Path

from .control_plane import ControlPlane, ControlPlaneConfig


def build_control_plane(args: argparse.Namespace) -> ControlPlane:
    config = ControlPlaneConfig(
        tenant_policy_path=args.tenant_policy,
        job_dir=args.job_dir,
        placements_path=args.placements,
    )
    return ControlPlane(config)


def cmd_list_jobs(cp: ControlPlane, args: argparse.Namespace) -> None:
    jobs = cp.list_jobs()
    print("\n".join(jobs))


def cmd_show_job(cp: ControlPlane, args: argparse.Namespace) -> None:
    job = cp.load_job(args.job_id)
    print(json.dumps({"id": job.id, "tasks": [task.id for task in job.tasks]}, indent=2))


def cmd_show_placements(cp: ControlPlane, args: argparse.Namespace) -> None:
    path = cp.config.placements_path
    if not path.exists():
        print("No placements recorded yet")
        return
    print(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Control Plane helper CLI")
    parser.add_argument("--tenant-policy", type=Path, default=Path(".orchestrator/tenant.yaml"))
    parser.add_argument("--job-dir", type=Path, default=Path(".orchestrator/jobs"))
    parser.add_argument("--placements", type=Path, default=Path(".orchestrator/placements.jsonl"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-jobs")
    show_job = sub.add_parser("show-job")
    show_job.add_argument("job_id")

    sub.add_parser("show-placements")

    args = parser.parse_args()
    cp = build_control_plane(args)
    match args.command:
        case "list-jobs":
            cmd_list_jobs(cp, args)
        case "show-job":
            cmd_show_job(cp, args)
        case "show-placements":
            cmd_show_placements(cp, args)


if __name__ == "__main__":  # pragma: no cover
    main()
