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

Add a new variables file (e.g. `<code>.tfvars`) with the entity's `scope`,
`region`, and `vm_size`, and run the existing Terraform module against the
new `prod` subscription:

```
terraform apply -var-file=<code>.tfvars
```

No new Terraform code is written for a new entity — only a new `.tfvars`
file. The module already provisions the resource group, VM, NSG, Key Vault,
mandatory tags, and budgets from the same code path used for `dti`.

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
(system updates, Python + uv, DuckDB, dbt Core + adapter, dbt MetricFlow,
Dagster OSS, Metabase, DataHub last). The script is idempotent by design, so
re-running it is always safe — see the
[Onboarding an engineer](onboarding-an-engineer.md) page for what each
installation step verifies before moving to the next.

## 5. Data platform code — new entity mono-repo

Create a new entity repository (`data-platform-<code>`) following the
structure in
[Repositories and delivery](repositories-and-delivery.md#entity-mono-repo-structure).
It links to this standards site rather than copying any of its content.

## 6. Data model — `entity` value, not a new table

The new entity's data lands in the **same** `dim_customer`, `fct_order`, etc.
tables as every other entity, distinguished by its `entity` column value
(e.g. `'bg'` for B&G) — not by a new set of entity-specific tables. See
[Data layers — multi-entity tables](data-layers.md#multi-entity-tables).

## 7. Budgets and tags — inherited, not recreated

Because the governance module is shared Terraform code, the new entity's
budgets and mandatory tags (`Entity=<code>`, `Environment`, `Workload`,
`Level`, `CostCenter`, `Owner`, `ManagedBy`) are created by the same
`terraform apply` in step 2 — not configured by hand afterward.

## What is not part of this procedure

- **A new storage account.** There is exactly one, group-wide — see
  [Azure landing zones](azure-landing-zones.md#resource-naming-pattern).
- **A new Azure Policy assignment.** Tag enforcement is assigned once, at
  `mg-picot-landingzones` scope, and applies automatically.
- **A copy of this standards repository.** Link to it; never fork or copy
  its content into the entity repository.
