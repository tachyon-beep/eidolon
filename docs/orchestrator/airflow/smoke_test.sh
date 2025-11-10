#!/usr/bin/env bash
set -euo pipefail
response=$(curl --fail --silent http://localhost:8080/health)
printf '%s
' "$response"
