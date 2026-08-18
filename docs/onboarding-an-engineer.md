# Onboarding an engineer

A reading order and a working local setup, aimed at getting a new team member
productive on an entity repository in about 30 minutes.

## 1. Read, in this order (about 10 minutes)

1. [Platform overview](platform-overview.md) — the end-to-end flow and why
   each tool is there.
2. [Data layers](data-layers.md) — the two axes (medallion vs. dbt layers)
   that are easy to conflate.
3. [Naming conventions](naming-conventions.md) — skim it once, then refer back
   to it while writing your first model rather than memorizing it up front.
4. The entity repository's own `README.md` and `docs/runbook.md` — anything
   specific to that entity's data sources and operational quirks lives there,
   not in this standards site.

Everything else ([Semantic layer](semantic-layer.md),
[Azure landing zones](azure-landing-zones.md),
[Repositories and delivery](repositories-and-delivery.md)) is reference
material — read it when the task at hand needs it, not up front.

## 2. Local dev setup (about 20 minutes)

Local development targets **dev**: a local DuckDB file, no cloud resources.
There is no need for Azure credentials to write and test a dbt model.

```bash
git clone <entity-repo-url>
cd data-platform-<entity>/transformation

# Python dependencies are pinned in pyproject.toml / uv.lock — use uv sync,
# not an ad hoc `uvx dbt`, to avoid version drift between contributors.
uv sync

cp profiles.yml.example profiles.yml
# Edit profiles.yml: point the "dev" target at a local .duckdb file path.
# profiles.yml is never committed — it can contain machine-specific paths
# or credentials.
```

Verify the setup, one tool at a time:

```bash
uv run dbt debug          # confirms the DuckDB connection resolves
uv run dbt seed           # loads any local seed/mock data
uv run dbt build          # runs every model + test against dev
```

If `dbt build` passes, the local environment is working end to end: models
compile, run against DuckDB, and pass their tests.

Everything stays in the local DuckDB file — `dbt build` writes nothing to ADLS.
Publishing Silver and Gold is a separate orchestration step that runs after the
build ([ADR 0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md)),
so a local build cannot affect what anyone else reads.

## 3. Your first model

Start from an existing `stg_` model as a template rather than from a blank
file — every staging model in the repo already follows the naming and
structure rules in [Naming conventions](naming-conventions.md#dbt-model-naming).
Before opening a pull request:

- Does the model have at least one test (`unique`, `not_null` on its key
  column)? A model without a test is not considered finished.
- Does it belong in `staging/`, `intermediate/`, `dimensions/`, `facts/`, or
  `marts/`? See [Data layers](data-layers.md) if unsure.
- Does the commit message follow
  [Conventional Commits](repositories-and-delivery.md#commits)?

## 4. If you're setting up the VM itself, not just a local dev environment

That's a separate procedure (`bootstrap_vm.sh`), not part of this 30-minute local
setup — and it is much shorter than it used to be: **system updates, Docker, `jq`
and `git`, and nothing else.** The platform ships as a container image built in
CI, so Python, uv, dbt and Dagster live inside that image; installing them on the
machine as well would create a second copy of the stack, resolved from different
versions, and "works on the VM" would stop meaning "works from the image".

Metabase is not installed on an entity VM: it runs once for the whole group on
the shared BI machine — see
[ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md).
No catalog service is installed either, on any machine: the catalog is the static
site `dbt docs generate` produces, attached to each CI run as an artifact and read
from there or with `dbt docs serve` — see
[ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md).

See the entity repository's `infra/scripts/bootstrap_vm.sh` and its
`docs/runbook.md`.
