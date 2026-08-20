# Data Platform Standards

Group-wide reference documentation for the Picot data platform: naming
conventions, Azure landing zone structure, data layering, semantic layer, and
delivery conventions (git, CI/CD). This is the single source of truth shared
across all entity repositories (`poc-data-platform-dti`, and future
per-entity production repos).

**Published site: <https://picot-data.github.io/data-platform-standards/>**

Architecture decisions and their reasoning live separately in [`adr/`](adr/),
kept apart from the reference docs so the rules stay short and unambiguous.

## Read it in your language

English is the single source of truth. French and Dutch are machine
translations, regenerated from it on every deploy — never hand-written or
committed — so they cannot drift out of sync (see
`scripts/translate_docs.py`). Diagrams stay in English on all three.

- 🇬🇧 [English](https://picot-data.github.io/data-platform-standards/)
- 🇫🇷 [Français](https://picot-data.github.io/data-platform-standards/fr/)
- 🇳🇱 [Nederlands](https://picot-data.github.io/data-platform-standards/nl/)

## Reading the docs

```
uv sync
uv run mkdocs serve
```

Then open http://127.0.0.1:8000.

## The standards as a Claude Code plugin

The dbt rules in `docs/` are also packaged as a Claude Code plugin, so an
agent applies them instead of an engineer remembering them. It lives in this
repository on purpose: a rule and the tool that enforces it move in the same
commit. Three skills — review a dbt YAML against the standards, generate a
model's test battery, draft descriptions without ever inventing a business
definition.

```
/plugin marketplace add picot-data/data-platform-standards
/plugin install picot-dbt-standards@picot-data-platform-standards
```

See [`plugins/picot-dbt-standards/`](plugins/picot-dbt-standards/) for what
each skill does and how updates are pulled.

## Structure

- `docs/` — reference documentation, published via MkDocs Material
- `adr/` — Architecture Decision Records (immutable, one per decision)
- `plugins/picot-dbt-standards/` — the standards as agent skills
- `.claude-plugin/marketplace.json` — makes this repository a plugin marketplace
- `.github/workflows/docs.yml` — builds and publishes the site to GitHub Pages on every push to `main`
