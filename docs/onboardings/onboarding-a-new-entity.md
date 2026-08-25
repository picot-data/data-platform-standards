# Onboarding a new entity

This is the repeatable procedure for bringing a new group entity (for example
`bg`, i.e. B&G) onto the data platform, once its diagnosis phase is complete
and its entity code is decided (see
[Azure landing zones](../azure-landing-zones.md#resource-naming-pattern)) — the
same code is used everywhere: Azure resource names, the `entity` column, and
ADLS folder prefixes.
Following this template rather than improvising is what makes the platform's
multi-entity claim credible — see
[ADR 0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md).

## 1. Governance — landing zone and subscriptions

Create the entity's landing zone management group and its three
subscriptions, following the exact template already in place for `dti`:

- Management group `mg-picot-lz-<code>`, under `mg-picot-landingzones`.
- Three subscriptions: `sub-picot-<code>-dev`, `sub-picot-<code>-staging`,
  `sub-picot-<code>-prod`.

This step usually requires org-level (EA/MCA) administrative rights the
platform owner may not personally hold — it is typically done once, outside
Terraform, by whoever holds tenant-level access. Terraform then targets the
existing `prod` subscription via a provider alias, rather than creating the
subscription itself.

Because tag `require` and `inherit` policies are assigned once at
`mg-picot-landingzones` scope (see
[ADR 0004](https://github.com/picot-data/data-platform-standards/blob/main/adr/0004-tagging-enforced-via-policy.md)),
the new landing zone inherits tag governance automatically — no separate
policy assignment is needed per entity.

## 2. Infrastructure — new `.tfvars`, same Terraform module

The Terraform code is not written per entity — it lives once in
`terraform-azure-data-platform`, versioned by Git tags
(see [ADR 0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md)),
as two modules: `modules/entity` (resource group, VM, NSG, Key Vault, the VM's
user-assigned managed identity, this entity's container registry, **and every role
assignment that identity needs**) and
`modules/governance` (budgets, action groups — see
[Azure landing zones — Everything in Terraform](../azure-landing-zones.md#everything-in-terraform)).
Mandatory tags are **not** part of either module — they stay a
`local.common_tags` block declared once in the entity's own root module and
merged into every resource, exactly as
[Azure landing zones](../azure-landing-zones.md#tagging-strategy) specifies;
folding them into `modules/governance` would make it depend on the resource
group `modules/entity` creates while `modules/entity` depends on its tags —
a dependency cycle.
The new entity's `infra/terraform/` (from the template repo, step 5) is a
thin root module that calls both, pinned to the same `ref`:

```hcl
locals {
  common_tags = {
    Entity      = var.entity
    Environment = var.environment
    # ... Workload, Level, CostCenter, Owner, ManagedBy — see naming-conventions.md
  }
}

module "platform" {
  source               = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/entity?ref=v2.2.0"
  entity               = var.entity
  region               = var.region
  vm_size              = var.vm_size
  admin_source_cidr    = var.admin_source_cidr
  admin_ssh_public_key = var.admin_ssh_public_key

  # Plain resource ids from this entity's .tfvars, not module references. The
  # module grants its VM identity data-plane access to the first, and grants the
  # CI deployer AcrPush plus the runCommand custom role using the second.
  shared_storage_account_id    = var.shared_storage_account_id
  github_deployer_principal_id = var.github_deployer_principal_id

  tags = local.common_tags
}

module "governance" {
  source              = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/governance?ref=v2.2.0"
  resource_group_id   = module.platform.resource_group_id
  resource_group_name = module.platform.resource_group_name
  budget_amount       = var.budget_amount # from finance, never invented
  budget_start_date   = var.budget_start_date # first day of a month, RFC3339
  notification_emails = [var.owner]
  tags                = local.common_tags
}
```

`shared_storage_account_id` looks optional — the module defaults it to null so
that an entity can be applied before the lake exists — and in practice it is
not. Without it the VM provisions perfectly and then fails **every** blob read
and write with a 403, because being subscription Owner covers the control plane
and the data plane is a separate RBAC system. DuckDB reports that 403 as
"this could mean the credentials used were wrong", which sends the investigation
after credentials that are fine. Read the id from the shared root module rather
than composing it by hand — Azure accepts a role assignment on a resource id that
does not exist, silently:

```
terraform -chdir=shared output -raw storage_account_id
```

A third module, `modules/storage`, exists in the same repository and is
**deliberately not called here**. It creates the group's shared ADLS account,
whose name is globally unique in Azure — a second entity calling it would either
fail or fight the first entity's state for the same resource. It is called once,
by the `shared/` root module in that same repository, which owns everything
existing once for the whole group (the lake today, the BI VM when it is created).

Add a new `<code>.tfvars` with the entity's values, then run:

```
terraform init
terraform plan  -var-file=<code>.tfvars -out=tfplan
terraform apply tfplan
```

**Always plan before applying, and apply the saved plan file rather than
re-running `apply` on its own.** Two different reasons:

- `apply` without a reviewed plan means the first time anyone sees what will
  change is while it is changing. On a bumped `ref` especially, a shared-module
  fix can produce a replacement rather than an update, and a replacement of the
  wrong resource is not recoverable by re-running Terraform.
- Applying `tfplan` guarantees Azure receives exactly what was reviewed. A bare
  `terraform apply -var-file=...` re-plans against whatever the world looks like
  at that moment, which is not necessarily what was on screen a minute earlier.

What to look for in the plan, every time: no `destroy` and no `replace` on
anything holding state or data — the storage account above all, then the VM's
managed identity and the Key Vault. Resources being *added* are normal on a
`ref` bump; resources being *removed* are a signal to stop and understand why.

No new Terraform code is written for a new entity — only a new `.tfvars`
file and a `ref` pin. That `ref` is pinned deliberately, not tracking
`main`: a fix landing in the shared module does not change an already-live
entity's infrastructure until that entity's root module is bumped to the
new tag and `terraform plan` has been reviewed.

## 3. Storage — new ADLS prefix, same storage account

The new entity does **not** get its own storage account — it uses the
existing group-wide `stpicotdata`, with a new folder prefix keyed by the
entity code from step 1 above — the same code, no separate data code (see
[Naming conventions — Cloud storage naming](../naming-conventions.md#cloud-storage-naming-adls)):

```
bronze/company_<entity>/...
silver/company_<entity>/...
gold/company_<entity>/...
```

Nothing is granted by hand here. Passing `shared_storage_account_id` in step 2 is
what makes `modules/entity` grant this entity's VM identity
`Storage Blob Data Contributor` on the account — scoped to the storage account,
never to the shared subscription. That assignment lives in the shared module
rather than in each entity's root module precisely so that onboarding an entity
writes no HCL at all
([ADR 0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md)).

Folder-level grants are not used: the assignment is on the account, and entity
separation inside it is by prefix. At Level 1 the entity VMs are operated by the
same team, so a data-plane boundary between prefixes would be a boundary nobody
is on the other side of. Revisit it when an entity has its own contributors.

## 4. Bootstrap — a container host, and nothing else

Run the `bootstrap_vm.sh` script from the entity template. It installs **Docker,
`jq` and `git`, and stops there**: system updates, the container runtime, and the
two utilities the deployment needs. It is idempotent by design, which is what
lets the VM be destroyed and recreated by Terraform without re-inventing the
install by hand.

**No Python, no uv, no dbt, no Dagster on the machine.** The platform ships as a
container image built in CI, so all of that lives *inside* the image; installing
it natively as well would create a second copy of the stack, resolved from
different versions, and "works on the VM" would stop meaning "works from the
image". The script did install them, on the first entity, before the platform was
containerised — that is history, not a fallback.

Neither Metabase nor the catalog is installed here: both run on the shared VM, the
only always-on machine — see step 8,
[ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)
and
[ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md).
What this VM owes the catalog is a publication step at the end of the run
([ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md)):
it deposits its dbt docs site on ADLS while it is awake, then shuts down.
An entity VM therefore runs the pipeline and nothing else, which is what lets it
be deallocated outside its window
([ADR 0018](https://github.com/picot-data/data-platform-standards/blob/main/adr/0018-scheduled-start-stop-for-entity-vms.md)) —
check that the entity's Dagster schedule sits inside that window.

## 5. Data platform code — new entity mono-repo

Create the new entity repository (`data-platform-<code>`) from the
`data-platform-entity-template` GitHub template repository ("Use this
template"), rather than creating one freehand — this is what makes the
structure in
[Repositories and delivery](../repositories-and-delivery.md#entity-mono-repo-structure)
actually identical across entities instead of merely documented as such.
The template's `<entity>` placeholders are filled in with `<code>` and
`infra/terraform/` is completed with the `ref` and `.tfvars` from step 2. It links
to this standards site rather than copying any of its content. What it does **not**
bring is a data model — its `transformation/` holds the project configuration and
no models at all, which is step 6's subject, not this one. Four steps in that
repo's README are easy to skip and each fails in its own way:

- **`shared_storage_account_id` in the `.tfvars`** — see step 2. The one omission
  that produces a working-looking VM that cannot touch the lake.
- **The source declaration and the ingestion asset's object list are the same
  list.** The dbt models reach Bronze through `source()`, and Dagster derives the
  asset key from that source — if the two disagree, nothing errors, the lineage
  simply splits into two disconnected graphs.
- **`uv lock` once in each of the three projects.** The template ships no
  lockfiles: a lockfile pins versions to the day it was written, and a stale one
  is worse than none. The image builds `--frozen`, so it fails loudly.
- **`dbt parse` once before starting Dagster.** The publication asset reads the
  manifest at import time, so definitions do not load until it exists.

The new repository's `ci.yml` calls the reusable workflow in
`data-platform-workflows`, which is **private** — so that repository's
*Settings → Actions → General → Access* must allow
"Accessible from repositories in the `picot-data` organization". It is a one-time
organisation-level setting, not a per-entity one, but it is worth knowing because
its absence fails with `workflow was not found`, which reads like a wrong path and
is not.

Because the template is copied once and not kept in sync afterward, an entity
generated a while ago can be behind it. That is the accepted trade-off of
ADR 0011 — the template is kept current against the reference entity rather than
being a fork of it, so the gap is always "the template is ahead", never "the
template is stale".

Because the template is copied once and not kept in sync afterward, a
structural change made to `data-platform-entity-template` later has to be
back-ported by hand to entities already onboarded — accepted at today's
scale (see ADR 0011).

## 6. Data model — `entity` value, not a new table

The new entity's data lands in the **same** `dim_customer`, `fct_order`, etc.
tables as every other entity, distinguished by its `entity` column value
(e.g. `'bg'` for B&G) — not by a new set of entity-specific tables. See
[Data layers — multi-entity tables](../building-a-data-model/data-layers.md#multi-entity-tables).

### Where this entity's models come from

The template ships **no models** — deliberately, since it holds the skeleton and
not the data model. So this is the step where an entity's `stg_`, `dim_`, `fct_`
and `mart_` models actually appear, and the two halves have different answers
(see
[Where a model's code comes from](../building-a-data-model/data-layers.md#where-a-models-code-comes-from)):

- **`staging/` is written for this entity**, against its own SAP. Not copied and
  adjusted — the point of the layer is to absorb what is specific here.
- **`int_`, `dim_`, `fct_` and `mart_` come from the shared dbt package**, added
  to `packages.yml` at a pinned revision. They are not written per entity, for
  the same reason no entity writes its own Terraform.

!!! warning "While the shared package does not exist yet"

    `data-platform-dbt-core` is decided and not built
    ([ADR 0024](https://github.com/picot-data/data-platform-standards/blob/main/adr/0024-conformed-models-as-a-shared-dbt-package.md)):
    the conformed layer is extracted once a second entity has been modelled, not
    designed before it. Until then the conformed models are copied from the
    reference entity, and **two rules make that copy reversible** rather than a
    permanent fork:

    - **The naming convention binds** — same model names, same column names, same
      units as the reference entity
      ([Column naming](../naming-conventions.md#column-naming)). Checked in this
      entity's pull requests, because it is the guard rail that fails silently:
      breach it and the extraction becomes a rewrite, discovered only at merge
      time.
    - **`gold_group` carries no `mart_`** until the marts come from one file. Facts
      and dimensions may be unioned — a divergence in raw measures shows up as two
      comparable numbers. A mart carries a definition, and `union_by_name`
      collapses two definitions into one column with no signal at all.

    Onboarding a **third** entity is the trigger to extract the package first, as
    is publishing the first group-level dashboard.

## 7. Budgets and tags — inherited, not recreated

The new entity's budgets and action groups come from `modules/governance`,
shared Terraform code in `terraform-azure-data-platform`; its mandatory tags
(`Entity=<code>`, `Environment`, `Workload`, `Level`, `CostCenter`, `Owner`,
`ManagedBy`) come from the `local.common_tags` block in its own root
module — the same pattern used for `dti`, not a new one invented per entity.
Both are created by the same `terraform apply` in step 2, not configured by
hand afterward.

## 8. BI — new scope on the existing instance

!!! note "Target, not current machinery"

    The shared BI machine does not exist yet: `vm-picot-shared-bi-weu-01` has no
    Terraform behind it (it is the second thing the `shared/` root module will
    own), and the reference entity currently runs Metabase on its own VM as a
    documented deviation. The steps below are what an entity is measured against.
    One prerequisite is recorded rather than assumed: Metabase's application
    database has to move from H2 to Postgres before it holds the whole group's
    users and dashboards.

The new entity does **not** get its own Metabase. On the shared VM
(`vm-picot-shared-bi-weu-01`):

- Add `<code>` to the refresh so it builds `serving_<code>.duckdb` from
  `gold/company_<code>/`, and includes the new folder in the unioned
  `gold_group` database.
- Add the serving file as a **read-only** Metabase database named `gold_<code>`.
  One database per entity is what makes entity isolation enforceable in the
  open-source edition — see
  [BI and access](../bi-and-access.md#data-permissions).
- Run `dbt-metabase models` against the new entity's manifest so its tables
  arrive documented, joined and with the technical ones hidden.
- Create the collection tree (entity at the top level, business domains below)
  and the two groups `<code>_analysts` and `<code>_readers`, then set data
  permissions before collection permissions.
- Grant `group_analysts` access to the new entity's database and collection —
  otherwise the group-level view silently keeps excluding it.
Nothing is added centrally for the catalog: the entity's CI builds its own dbt
docs site from its own project, so onboarding costs zero catalog configuration
([ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md)).
Once the entity has dashboards, `dbt-metabase exposures` is run against this
instance and its output committed to the entity repository, so lineage reaches
those dashboards — see
[ADR 0022](https://github.com/picot-data/data-platform-standards/blob/main/adr/0022-business-logic-in-dbt-metabase-is-presentation.md).

The full specification of collections, groups and permissions is in
[BI and access](../bi-and-access.md); this step applies it, it does not restate it.

## What is not part of this procedure

- **A new storage account.** There is exactly one, group-wide — see
  [Azure landing zones](../azure-landing-zones.md#resource-naming-pattern).
- **A new Metabase instance.** There is exactly one, group-wide — see
  [ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md).
- **A catalog service.** There is none to install: the catalog is generated by
  the entity's own CI — see
  [ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md).
- **A new Azure Policy assignment.** Tag enforcement is assigned once, at
  `mg-picot-landingzones` scope, and applies automatically.
- **A copy of this standards repository.** Link to it; never fork or copy
  its content into the entity repository.
- **A copy of the Terraform module or the CI workflow.** Reference
  `terraform-azure-data-platform` and `data-platform-workflows` by a pinned
  `ref`; never paste their contents into the entity repository.
