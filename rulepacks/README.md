# Rulepack Catalog

Published rulepacks live under `rulepacks/<pack-name>/rulepack.yaml`. Each pack directory should also contain any
compiled artefacts (e.g., `compiled/*.json`) and change notes. Use semantic versioning for each pack and keep the
metadata `version` field aligned with the directory contents.

## Available Packs

- `layering-core` (`RP-LAYERING-CORE`): enforces subsystem layering boundaries for UI/App/Data tiers and keeps per-
  boundary size under control.
- `security-call-ban` (`RP-SECURITY-CALL-BAN`): prohibits dangerous runtime evaluation helpers and guards against
  boundary packages reaching into prohibited sinks.

To publish a new pack:

1. Author/update `rulepack.yaml` in the pack directory.
2. Run `uv run eidolon-rulepack test rulepacks/<pack>/rulepack.yaml --show-sql` to verify selectors.
3. Run `uv run eidolon-rulepack publish rulepacks/<pack>/rulepack.yaml --output rulepacks/<pack>/compiled/v<version>.json`.
4. Reference the compiled artefact ID (`metadata.id` + `version`) from drift jobs and GateChecks.
