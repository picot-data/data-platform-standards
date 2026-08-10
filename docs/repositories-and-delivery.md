# Repositories and delivery

## Repository topology

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/repositories-and-delivery.svg"
</div>

`data-platform-standards` holds group-wide rules and decisions only — no
entity-specific code or data. Every entity repository implements these rules
and links back to this site rather than duplicating any of it. This is a
deliberate constraint: the first time a naming rule is copy-pasted into an
entity repo instead of linked, it starts drifting the moment either copy is
edited.

## Why one repo per entity, not one mega mono-repo for the whole group

Within a single entity, ingestion, transformation, orchestration, and
infrastructure code live together in **one mono-repo** — not split into
separate repos per component. A schema change in ingestion impacts dbt
models; in a mono-repo that's one commit, in a split-repo setup it's a dance
of synchronized pull requests across repositories. Splitting by *component*
only pays off once multiple contributors need independent release cadences
per component, which a single-owner Level 1 platform does not have.

Across entities, the boundary is different: each entity gets its **own**
mono-repo (`poc-data-platform-dti` today, a future `data-platform-<code>` in
production), rather than one repository shared by every entity. This follows
the same reasoning as one VM per entity
([ADR 0006](https://github.com/picot-data/data-platform-standards/blob/main/adr/0006-single-vm-for-level-1.md)):
each entity has its own Azure subscription, its own access boundary, and
potentially its own contributors — a shared repository would force shared
write access across entities that don't need it.

## Three shared repos, deduplicated once, not per entity

"Same module, same skeleton, same CI" across entities only holds if that
sameness is backed by something other than copy-paste. Three small repos
carry what would otherwise be duplicated into every entity mono-repo (see
[ADR 0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md)):

| Repo | Carries | Consumed by an entity repo as |
|---|---|---|
| `terraform-azure-data-platform` | The actual Terraform code, as two modules: `modules/entity` (resource group, VM, NSG, Key Vault) and `modules/governance` (budgets, action groups) — mandatory tags stay a `local.common_tags` block in the entity's own root module | `infra/terraform/` — a thin root module calling both, pinned to a tagged `ref` |
| `data-platform-entity-template` | The mono-repo skeleton below, as a GitHub template repository | "Use this template", once, when the entity repo is created |
| `data-platform-workflows` | The reusable CI workflow | `ci.yml` — a few lines calling it with `uses:` |

The distinction that matters: the Terraform module and the CI workflow stay
**live references** — bumping a `ref` pulls in a fix without touching the
entity repo's own code. The template is **copied once** — a structural
change made to it later has to be back-ported by hand to entities already
onboarded, which is an accepted trade-off at two to three entities (see
ADR 0011's consequences for when to revisit it).

## Entity mono-repo structure

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/entity-mono-repo-structure.svg"
</div>

Governance documentation (naming, tagging, landing zones, data layers,
semantic layer) is **not** duplicated here — it lives in
[data-platform-standards](index.md) and is linked from this repo's `README.md`.
Within `infra/terraform/`, only a root module (backend config, provider
alias, a call into `terraform-azure-data-platform` pinned to a `ref`, and
the entity's `<code>.tfvars`) lives in the entity repo — the module code
itself does not, per the table above.

## Branching

| Type | Pattern | Example |
|---|---|---|
| Main branch | `main` | — |
| Integration branch | `develop` | — |
| Feature | `feature/<domain>/<short-desc>` | `feature/ingestion/sap-sales-connector` |
| Bugfix | `fix/<short-desc>` | `fix/stg-order-duplicates` |

`feature/` and `fix/` branches merge into `develop`; `develop` merges into
`main` once its content is ready to deploy. No separate `release/<version>`
branch — `main` always reflects what is (or is about to be) live.

## Commits

Pattern: `<type>(<scope>): <description>`, following
[Conventional Commits](https://www.conventionalcommits.org/).

- **Type**: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`,
  `test`, `build`, `ci`
- **Subject**: imperative present tense, no trailing period, lowercase
  after the colon, 72 characters max
- **Scope**: optional — the module or folder touched (e.g. `ingestion`,
  `dbt`, `ci`)
- **Body**: for a diff bigger than ~20 lines or more than one concern —
  explains *why*, not *what*
- **Footer**: `BREAKING CHANGE:` when relevant, `Refs #123` when an issue
  is mentioned
- **Language**: match whatever the repository's existing commits use —
  English by default

## Minimal CI/CD

Every entity repository runs, at minimum, a `ci.yml` workflow on every push
and pull request. The steps below are implemented once, in
`data-platform-workflows`, as a reusable `workflow_call` workflow — an
entity's own `ci.yml` is a few lines calling it with `uses:`, not a
copy of the steps:

1. **Lint** the code (Python, SQL/dbt style).
2. **`dbt parse`** — catches syntax and reference errors without touching any
   data. This answers "does it compile?", not "does it work?".
3. **`dbt build --target dev`** (or dbt unit tests) — runs the models and
   their tests against dev data. This answers "does it work on data?".

A `deploy.yml` workflow, deploying merged code to the entity's VM, is
optional for a single-owner platform and must be explicitly documented as
*not implemented* rather than left ambiguous if it isn't built — a manual
deployment procedure written down in the entity's `runbook.md` is preferable
to a half-working deploy pipeline that looks automated but silently isn't.

This CI/CD discipline is what answers the question a steering committee will
ask sooner or later: *"how do we know this isn't hand-patched on the VM?"* —
the answer is that code is tested before it is deployed, not modified
directly on the machine that runs it.

## This standards repository's own delivery

`data-platform-standards` builds and publishes its own site via
`.github/workflows/docs.yml`: every push to `main` builds the MkDocs site and
deploys it to GitHub Pages. There is no separate dev/staging step for
documentation — a broken build fails the workflow and nothing gets
published, which is enough gatekeeping for a documentation site.
