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
| `terraform-azure-data-platform` | The actual Terraform code: `modules/entity` (resource group, VM, NSG, Key Vault, the VM's user-assigned managed identity, the entity's container registry, and every role assignment that identity needs), `modules/governance` (budgets, action groups), `modules/storage` (the group's lake) and `shared/` — the root module for what exists once for the whole group. Mandatory tags stay a `local.common_tags` block in each root module | `infra/terraform/` — a thin root module calling `entity` and `governance`, pinned to a tagged `ref`. Never `storage` or `shared/`: those are group-scoped |
| `data-platform-entity-template` | The mono-repo skeleton below, as a GitHub template repository | "Use this template", once, when the entity repo is created |
| `data-platform-workflows` | The reusable CI workflow | `ci.yml` — a few lines calling it with `uses:` |

The distinction that matters: the Terraform module and the CI workflow stay
**live references** — bumping a `ref` pulls in a fix without touching the
entity repo's own code. The template is **copied once** — a structural
change made to it later has to be back-ported by hand to entities already
onboarded, which is an accepted trade-off at two to three entities (see
ADR 0011's consequences for when to revisit it).

## Making a change — which repo, then what

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/repo-relationships-and-change-playbook.svg"
</div>

The table above the fold restates the relationships as a lookup rather than
a topology — useful the moment the actual question is "I need to change
X, where do I do that and what else do I need to run?" rather than "how is
this organized?". The two amber rows are the one thing this setup does not
deduplicate automatically: a structural change to the template, and a new
mandatory tag, both have to be applied by hand to every entity repo that
already exists. That's an accepted trade-off at today's scale (two to three
entities) — see [ADR 0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md)'s
consequences for when to revisit it.

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

1. **Lint** the Python, with the `ruff` version the entity repo itself pins — a
   lint failing because the tool moved is indistinguishable from one failing
   because the code did.
2. **`dbt parse`** — resolves every `ref()`, `source()` and macro and validates
   every schema file, without touching any data. This answers "does it compile?",
   not "does it work?".
3. **dbt unit tests** — executes the transformation logic against inline
   fixtures. This answers "does it work on data?" *without a credential*, which
   is what allows it to run on every push from every branch.

Step 3 is deliberately **not** `dbt build`. Building runs against real data, which
means a storage credential in GitHub secrets, and keeping CI credential-free is
worth more than the extra coverage — especially since unit tests cover cases real
data only produces months later, such as Bronze holding several daily partitions
at once.

Deployment to the entity's VM is a separate pipeline, described in
[Deployment](#deployment) below.

This CI/CD discipline is what answers the question a steering committee will
ask sooner or later: *"how do we know this isn't hand-patched on the VM?"* —
the answer is that code is tested before it is deployed, not modified
directly on the machine that runs it.

## Deployment

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/deployment-flow.svg"
</div>

The platform is deployed as a **container image**, built once in CI and pulled
by the entity's VM. The VM holds no checkout of the repository, no toolchain
beyond a container runtime, and no credential — see
[ADR 0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md)
for why this shape was chosen over a self-hosted runner.

**Implementation status.** This describes the standard, not what is running
today. No entity meets it yet: the OIDC half needs an Entra ID app
registration, and the tenant currently forbids a normal user from creating one
(`allowedToCreateApps = false`), so an IT request is pending. Until it lands,
`poc-data-platform-dti` deploys through a self-hosted runner pulling from GHCR
with a stored token — the shape ADR 0012 explicitly rejects. That gap is
recorded in that repository's *Known deviations from the standards*, which is
where an entity's distance from this page belongs. Read the four rules below as
what an entity is measured against, not as a description of the current
machinery.

Four rules define the pipeline:

1. **A deployment names an exact build.** The image is tagged
   `sha-<commit>` and a deployment always references that tag, never `:latest`
   and never a branch name. Without this, *"what is running on the VM?"* has no
   answer and a rollback has no target.
2. **No secret is stored anywhere in the path.** GitHub authenticates to Azure
   with an OIDC federated credential, and the VM pulls from **its entity's own**
   container registry with its own managed identity (`AcrPull`). Every credential
   involved is minted per run and expires. The registry is per entity, not
   shared: ACR grants `AcrPull`/`AcrPush` over a whole registry, so a shared one
   would let any entity's CI overwrite another entity's images.
3. **Nothing reaches the VM inbound.** The NSG allows SSH from a single admin
   CIDR and nothing else. The deployment travels over the Azure control plane
   via Run Command, so no port is opened and no agent of GitHub's runs on the
   machine. The role granted to GitHub is a custom one limited to
   `Microsoft.Compute/virtualMachines/runCommand/action` — never
   `Virtual Machine Contributor`, which could delete the VM.
4. **A deployment is approved, and the approval is enforced by Azure.** The
   deploy job targets a GitHub Environment named `production` carrying required
   reviewers, and the federated credential's subject is bound to that
   environment (`repo:picot-data/<entity-repo>:environment:production`). A run
   that skipped the gate cannot obtain an Azure token, so the approval is not
   something a workflow edit can remove.

Only `main` deploys. A pull request builds the image and never publishes it; a
push to the integration branch publishes an image without touching any VM. A
manual `workflow_dispatch` naming an existing tag is the rollback path, and
skips the build entirely rather than producing a different tag than the one
being deployed.

A deployment reports success only once the platform **answers** — the script
polls the Dagster webserver before going green. "Containers created" is not
"platform working": a broken dbt profile or a failed import surfaces only when
the code server starts.

## This standards repository's own delivery

`data-platform-standards` builds and publishes its own site via
`.github/workflows/docs.yml`: every push to `main` builds the MkDocs site and
deploys it to GitHub Pages. There is no separate dev/staging step for
documentation — a broken build fails the workflow and nothing gets
published, which is enough gatekeeping for a documentation site.
