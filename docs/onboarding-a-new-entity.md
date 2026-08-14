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
  source  = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/entity?ref=v1.2.0"
  entity  = "<code>"
  region  = "westeurope"
  vm_size = "Standard_D4s_v5"
  tags    = local.common_tags
}

module "governance" {
  source              = "git::https://github.com/picot-data/terraform-azure-data-platform.git//modules/governance?ref=v1.2.0"
  entity              = "<code>"
  resource_group_id   = module.platform.resource_group_id
  budget_amount       = var.budget_amount # from finance, never invented
  tags                = local.common_tags
}
```

Add a new `<code>.tfvars` with the entity's values, then run:

```
terraform init
terraform apply -var-file=<code>.tfvars
```

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
(system updates, Python + uv, DuckDB, dbt Core + adapter, Dagster OSS,
Metabase, DataHub last). The script is idempotent by design, so
re-running it is always safe — see the
[Onboarding an engineer](onboarding-an-engineer.md) page for what each
installation step verifies before moving to the next.

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

## What is not part of this procedure

- **A new storage account.** There is exactly one, group-wide — see
  [Azure landing zones](azure-landing-zones.md#resource-naming-pattern).
- **A new Azure Policy assignment.** Tag enforcement is assigned once, at
  `mg-picot-landingzones` scope, and applies automatically.
- **A copy of this standards repository.** Link to it; never fork or copy
  its content into the entity repository.
- **A copy of the Terraform module or the CI workflow.** Reference
  `terraform-azure-data-platform` and `data-platform-workflows` by a pinned
  `ref`; never paste their contents into the entity repository.
