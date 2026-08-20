# Onboarding a data engineer

For the person who will write dbt models, run the pipeline and open pull
requests on an entity repository. A reading order and a working local setup,
aimed at productive in about 30 minutes.

If you build questions and dashboards in Metabase and will never open the
repository, read [Onboarding a data analyst](onboarding-a-data-analyst.md)
instead — and read it anyway once you are set up, because it is where the
boundary between a dbt model and a Metabase question is drawn, and half of that
boundary is yours to hold.

## 1. Read, in this order (about 10 minutes)

1. [Platform overview](platform-overview.md) — the end-to-end flow and why
   each tool is there.
2. [Data layers](data-layers.md) — the two axes (medallion vs. dbt layers)
   that are easy to conflate, and where each layer persists.
3. [dbt project structure](project-structure.md) — which folder a model goes
   in, and why the folder is configuration rather than tidiness.
4. [Naming conventions](naming-conventions.md) — skim it once, then refer back
   to it while writing your first model rather than memorizing it up front.
5. The entity repository's own `README.md` and `docs/runbook.md` — anything
   specific to that entity's data sources and operational quirks lives there,
   not in this standards site.

[Writing descriptions](writing-descriptions.md) and [Testing](testing.md) are
not on that list because reading them cold teaches little. You need them at the
moment you finish your first model, which is step 3 below.

Everything else ([Metric definitions](metric-definitions.md),
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

A model is finished when it is described and tested, not when it compiles.
Before opening a pull request:

- Is it in the right folder — `staging/`, `intermediate/`, `dimensions/`,
  `facts/` or `marts/`, and the right sub-folder within it? See
  [Data layers](data-layers.md) and
  [dbt project structure](project-structure.md).
- Does every model and every column carry a `description` that says something
  the name does not? CI fails on a missing one, and a description that restates
  the column name passes CI while teaching nothing — see
  [Writing descriptions](writing-descriptions.md).
- Do its tests assert the guarantee this model creates, rather than one the
  warehouse already enforces? [Testing](testing.md) has the minimum bar per
  layer and the anti-patterns worth knowing before you hit them.
- Does the commit message follow
  [Conventional Commits](repositories-and-delivery.md#commits)?

## 4. If you're setting up the VM itself, not just a local dev environment

That's a separate procedure (`bootstrap_vm.sh`), not part of this 30-minute local
setup — and it is much shorter than it used to be: **system updates, Docker, `jq`
and `git`, and nothing else.** The platform ships as a container image built in
CI, so Python, uv, dbt and Dagster live inside that image; installing them on the
machine as well would create a second copy of the stack, resolved from different
versions, and "works on the VM" would stop meaning "works from the image".

Neither Metabase nor the catalog is installed on an entity VM. Both live on the
shared BI machine, the only one always on — see
[ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)
and
[ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md).
The catalog is the static site `dbt docs generate` produces
([ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md)),
browsable at `/catalog/<entity>/` from the corporate network. What this repo's
pipeline owes it is a publication step, not a service.

See the entity repository's `infra/scripts/bootstrap_vm.sh` and its
`docs/runbook.md`.
