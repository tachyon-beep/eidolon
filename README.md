# Eidolon

This repo contains the Eidolon platform code and the design library under `docs/design/`. The design tree is organised by audience and lifecycle so contributors can find specs quickly and apply consistent review policies.

## Design structure

- `docs/design/00-foundation/` – system HLD, CodeGraph, data model, and refiner workflow basics.
- `docs/design/10-runtime/` – runtime execution topics: orchestration, caching, determinism, drift, integrations.
- `docs/design/20-governance/` – security, supply chain, agent guardrails, observability, and UX resilience.
- `docs/design/30-role-guides/` – (placeholder) role-specific playbooks for Operator/Coder/Architect/Product Owner.

Each subfolder carries its own `README.md` plus the specs that belong to that domain. See `docs/design/README.md` for the ASCII map.

See `docs/README.md` for documentation standards (including mandatory frontmatter for every doc).
