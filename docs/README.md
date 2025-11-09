# Documentation Standards

The `docs/` tree collects the design library and any supplemental documentation. All documents in this tree must start with an AI-friendly frontmatter block so automation can decide whether to load a file without scanning its full contents.

## Structure

- `design/` – primary design library (see `docs/design/README.md` for layout and contents)
- (future paths can be added as the documentation set grows)

## Mandatory frontmatter

Every document under `docs/` must begin with a YAML frontmatter block:

```yaml
---
id: <SPEC-ID or doc slug>
version: <semver or date>
owner: <team/person>
status: <draft|review|approved|deprecated>
summary: <1-2 sentence overview>
tags:
  - <keywords>
last_updated: <YYYY-MM-DD>
---
```

Guidance:
- `id` should match the canonical spec identifier (e.g., `SEC-01`) or a unique slug.
- Keep `summary` concise but specific; mention audience and scope.
- Update `last_updated` whenever substantive content changes.
- Files lacking this header should be treated as policy violations.

## Review policy

When editing docs:
1. Ensure the frontmatter is present and up to date.
2. Keep references and links in sync with the folder structure.
3. Note significant decisions or changes in commit messages for traceability.
