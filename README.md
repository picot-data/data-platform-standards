# Data Platform Standards

Group-wide reference documentation for the Picot data platform: naming
conventions, Azure landing zone structure, data layering, semantic layer, and
delivery conventions (git, CI/CD). This is the single source of truth shared
across all entity repositories (`poc-data-platform-dti`, and future
per-entity production repos).

Architecture decisions and their reasoning live separately in [`adr/`](adr/),
kept apart from the reference docs so the rules stay short and unambiguous.

## Reading the docs

```
uv sync
uv run mkdocs serve
```

Then open http://127.0.0.1:8000.

## Structure

- `docs/` — reference documentation, published via MkDocs Material
- `adr/` — Architecture Decision Records (immutable, one per decision)
- `.github/workflows/docs.yml` — builds and publishes the site to GitHub Pages on every push to `main`
