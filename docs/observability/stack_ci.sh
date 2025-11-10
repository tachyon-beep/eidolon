#!/usr/bin/env bash
set -euo pipefail
cd docs/observability
docker compose up -d
trap "docker compose down" EXIT
sleep 5
uv run python sample_telemetry.py
