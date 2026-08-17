# Onboarding a new entity

This is the repeatable procedure for bringing a new group entity (for example
`bg`, i.e. B&G) onto the data platform, once its diagnosis phase is complete
and its entity code is decided (see
[Azure landing zones](azure-landing-zones.md#resource-naming-pattern)) — the
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
as two modules: `modules/entity` (resource group, VM, NSG, Key Vault) and
`modules/governance` (budgets, action groups — see
[Azure landing zones — Everything in Terraform](azure-landing-zones.md#everything-in-terraform)).
Mandatory tags are **not** part of either module — they stay a
`local.common_tags` block declared once in the entity's own root module and
merged into every resource, exactly as
[Azure landing zones](azure-landing-zones.md#tagging-strategy) specifies;
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
  source  = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/entity?ref=v2.1.0"
  entity  = "<code>"
  region  = "westeurope"
  vm_size = "Standard_D4s_v5"
  tags    = local.common_tags
}

module "governance" {
  source              = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/governance?ref=v2.1.0"
  entity              = "<code>"
  resource_group_id   = module.platform.resource_group_id
  budget_amount       = var.budget_amount # from finance, never invented
  tags                = local.common_tags
}
```

A third module, `modules/storage`, exists in the same repository and is
**deliberately not called here**. It creates the group's shared ADLS account,
whose name is globally unique in Azure — a second entity calling it would
either fail or fight the first entity's state for the same resource. It is
called once, by whichever root module owns the shared subscription.

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
[Naming conventions — Cloud storage naming](naming-conventions.md#cloud-storage-naming-adls)):

```
bronze/company_<entity>/...
silver/company_<entity>/...
gold/company_<entity>/...
```

Grant the new VM's managed identity `Storage Blob Data Contributor` on the
relevant containers/folders — scoped to the storage account, not to the
entire shared subscription.

## 4. Bootstrap — same script, same order

Run the same `bootstrap_vm.sh` script used for `dti`, in the same order
(system updates, Python + uv, DuckDB, dbt Core + adapter, Dagster OSS last).
The script is idempotent by design, so re-running it is always safe — see the
[Onboarding an engineer](onboarding-an-engineer.md) page for what each
installation step verifies before moving to the next.

Neither Metabase nor DataHub is installed here. Both run once for the whole
group on the shared VM — see step 8,
[ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)
and
[ADR 0019](https://github.com/picot-data/data-platform-standards/blob/main/adr/0019-datahub-joins-the-shared-vm.md).
An entity VM therefore runs the pipeline and nothing else, which is what lets it
be deallocated outside its window
([ADR 0018](https://github.com/picot-data/data-platform-standards/blob/main/adr/0018-scheduled-start-stop-for-entity-vms.md)) —
check that the entity's Dagster schedule sits inside that window.

## 5. Data platform code — new entity mono-repo

Create the new entity repository (`data-platform-<code>`) from the
`data-platform-entity-template` GitHub template repository ("Use this
template"), rather than creating one freehand — this is what makes the
structure in
[Repositories and delivery](repositories-and-delivery.md#entity-mono-repo-structure)
actually identical across entities instead of merely documented as such.
The template's `<entity>` placeholders (folder names, `pyproject.toml`,
`ci.yml`'s call into `data-platform-workflows`) are filled in with `<code>`;
`infra/terraform/` is completed with the `ref` and `.tfvars` from step 2. It
links to this standards site rather than copying any of its content.

Because the template is copied once and not kept in sync afterward, a
structural change made to `data-platform-entity-template` later has to be
back-ported by hand to entities already onboarded — accepted at today's
scale (see ADR 0011).

## 6. Data model — `entity` value, not a new table

The new entity's data lands in the **same** `dim_customer`, `fct_order`, etc.
tables as every other entity, distinguished by its `entity` column value
(e.g. `'bg'` for B&G) — not by a new set of entity-specific tables. See
[Data layers — multi-entity tables](data-layers.md#multi-entity-tables).

## 7. Budgets and tags — inherited, not recreated

The new entity's budgets and action groups come from `modules/governance`,
shared Terraform code in `terraform-azure-data-platform`; its mandatory tags
(`Entity=<code>`, `Environment`, `Workload`, `Level`, `CostCenter`, `Owner`,
`ManagedBy`) come from the `local.common_tags` block in its own root
module — the same pattern used for `dti`, not a new one invented per entity.
Both are created by the same `terraform apply` in step 2, not configured by
hand afterward.

## 8. BI and catalog — new scope on the existing instances

The new entity does **not** get its own Metabase or its own DataHub. On the
shared VM (`vm-picot-shared-bi-weu-01`):

- Add `<code>` to the refresh so it builds `serving_<code>.duckdb` from
  `gold/company_<code>/`, and includes the new folder in the unioned
  `gold_group` database.
- Add the serving file as a **read-only** Metabase database named `gold_<code>`.
  One database per entity is what makes entity isolation enforceable in the
  open-source edition — see
  [BI and access](bi-and-access.md#data-permissions).
- Run `dbt-metabase models` against the new entity's manifest so its tables
  arrive documented, joined and with the technical ones hidden.
- Create the collection tree (entity at the top level, business domains below)
  and the three groups `<code>_analysts`, `<code>_explorers` and
  `<code>_readers`, then set data permissions before collection permissions.
- Grant `group_analysts` access to the new entity's database and collection —
  otherwise the group-level view silently keeps excluding it.
- Add the entity's `metadata/company_<code>/` prefix to the DataHub ingestion
  recipe, so its dbt models appear in the existing catalog and its lineage joins
  the group graph. No new DataHub instance, no new glossary.

The full specification of collections, groups and permissions is in
[BI and access](bi-and-access.md); this step applies it, it does not restate it.

## What is not part of this procedure

- **A new storage account.** There is exactly one, group-wide — see
  [Azure landing zones](azure-landing-zones.md#resource-naming-pattern).
- **A new Metabase or DataHub instance.** There is exactly one of each,
  group-wide — see
  [ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)
  and
  [ADR 0019](https://github.com/picot-data/data-platform-standards/blob/main/adr/0019-datahub-joins-the-shared-vm.md).
- **A new Azure Policy assignment.** Tag enforcement is assigned once, at
  `mg-picot-landingzones` scope, and applies automatically.
- **A copy of this standards repository.** Link to it; never fork or copy
  its content into the entity repository.
- **A copy of the Terraform module or the CI workflow.** Reference
  `terraform-azure-data-platform` and `data-platform-workflows` by a pinned
  `ref`; never paste their contents into the entity repository.
