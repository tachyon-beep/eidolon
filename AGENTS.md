# Repository Guidelines

## Project Structure & Module Organization

- `src/eidolon/` holds all Python packages. Key modules today live under `codegraph/` (scanner, generators, ingest/query tools) and grow as features land.
- `docs/design/` contains the architecture corpus (HLD, runtime, governance, rapid designs). `docs/governance/` stores risk/issue registers.
- `benchmarks/` (ignored by Git) is the scratchpad for synthetic datasets, scan reports, and external repos (e.g., `benchmarks/cpython`).
- Tests will reside under `tests/` mirroring the package layout (e.g., `tests/codegraph/test_scanner.py`).

## Build, Test, and Development Commands

- `uv sync` – install/update dependencies defined in `pyproject.toml`.
- `uv run eidolon-codegraph-scan <repo>` – benchmark the scanner, optionally writing `--records` JSONL and `--summary` JSON.
- `uv run eidolon-synthesize-repo <dir>` – generate a synthetic Python corpus for scale tests.
- `uv run eidolon-codegraph-ingest <records> --summary <summary>` – load scanner output into Postgres (ensure the container is running on `localhost:6543`).
- Planned: `uv run pytest` once unit tests exist; keep fixtures lightweight.

## Coding Style & Naming Conventions

- Python 3.13+, type hints required. Follow PEP 8 with 4-space indentation and snake_case for modules/functions; PascalCase for dataclasses.
- Use descriptive filenames (`codegraph/ingest.py`, not `cg_ing.py`). CLI entry points live under `[project.scripts]` in `pyproject.toml`.
- Run `uv format` / `ruff` (to be added) before committing; keep imports sorted.

## Testing Guidelines

- Target `pytest` with `tests/<package>/test_*.py`. Name tests after behavior (`test_scanner_handles_rename`).
- Include synthetic fixtures under `benchmarks/` or `tests/fixtures/`; cap runtime so `pytest` finishes within minutes.
- Add regression tests when fixing bugs in scanners or ingest.

## Commit & Pull Request Guidelines

- Commit messages follow `<area>: <imperative summary>` (e.g., `codegraph: add concurrency benchmark`). Keep scope focused.
- PRs should include: summary of changes, testing evidence (`uv run ...` output), and links to relevant docs (e.g., RAPID designs). Attach screenshots for UX-affecting work.

## Rapid Plan Status (internal roadmap)
- **CodeGraph (RAPID-CG-SCALE)** – ✅ completed. Scanner/ingest/query risks closed; see `docs/design/rapid/CODEGRAPH_RAPID.md` and `benchmarks/reports/*.json`.
- **Rulepack DSL** – 🔄 in progress. Implementation plan captured in `docs/design/rapid/RULEPACK_RAPID.md`; next up is schema + compiler spike.
- **TaskSpec Residency** – 📝 planned. Rapid design pending; follow SEC-01 guidance once Rulepack lands.
- **Product LLM bridge** – 📝 planned. Sanitised Balanced mode documented in SEC-01; awaiting engineering slot.

## Security & Configuration Tips

- Never run `sudo` inside this repo. Reset Postgres volumes via Docker containers, e.g. `docker stop eidolon-pg && docker run --rm -v "$(pwd)/postgres-data:/var/lib/postgresql/data" busybox sh -c 'rm -rf /var/lib/postgresql/data/*'`, then recreate the container.
- Prefer `docker compose up -d postgres` (see `docker-compose.yml`) to start the DB; `docker compose down` stops it cleanly.
- Secrets are not part of this project; local `.env` or Postgres credentials should remain in your shell, not committed.
