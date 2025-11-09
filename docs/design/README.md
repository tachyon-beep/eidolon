# Eidolon Design Library

```
docs/design/
├── 00-foundation/      # Core architecture, data model, code graph, refiner loop
├── 10-runtime/         # Control plane execution, caching, determinism, integrations
├── 20-governance/      # Security, guardrails, supply chain, observability, UX
├── 30-role-guides/     # Operator/Coder/Architect/Product Owner playbooks
└── rapid/              # Rapid design spikes for high-risk components
```

Each subfolder contains a `README.md` describing its focus and inventory. All individual specs include AI-friendly frontmatter (see root `README.md` for the rule) so automation can triage documents quickly.
