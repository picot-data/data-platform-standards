# Technical architecture dossier

The technical architecture dossier (DAT, *dossier d'architecture technique*)
describes the Level 1 platform **as a system**: what is deployed, where, how the
parts connect, who can reach what, and how it is kept running. The rest of this
site is normative — how any entity must be built. This page is descriptive — what
this platform is.

It does not repeat reasoning. Every choice links to the ADR that made it; the
rules live on their own pages. Each item carries a status:

- **Deployed** — exists in Azure and matches this dossier.
- **Coded** — in Terraform, not yet applied.
- **Target** — decided, not built.
- **Gap** — neither decided nor built; listed in [Open items](#open-items).

| Document control | |
|---|---|
| Version | 0.1 — draft |
| Date | 2026-09-30 |
| Owner | Platform owner, data team |
| Status | Not yet reviewed. Circulated to the SAP contractor for comment |
| Scope | Level 1, first entity (Dirickx, `dti`) and the group-shared scope |

!!! warning "What this public page leaves out"
    This site is published publicly. IP addresses, subscription ids, host names
    and the contractor's network details are **not** written here; they belong in
    a restricted annex. Everything below is at the level of resource names and
    patterns.

## 1. Architecture at a glance

The end-to-end flow and its diagram are in
[Platform overview](platform-overview.md). In one line per stage:

1. **Extraction.** Azure Data Factory reads SAP tables through a self-hosted
   integration runtime (SHIR) installed inside the network that can reach SAP,
   and lands them as Parquet in `bronze`
   ([ADR 0010](https://github.com/picot-data/data-platform-standards/blob/main/adr/0010-adf-not-python-scripts-for-sap.md)).
2. **Transformation.** On the entity VM, Dagster mirrors Bronze locally, runs dbt
   on DuckDB, and publishes Silver and Gold back to the lake
   ([ADR 0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md)).
3. **Consumption.** On the shared BI VM, a scheduled refresh pulls Gold and the
   dbt docs site; Metabase and the catalog are served from there
   ([ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md),
   [ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md)).

## 2. Azure organisation

Target structure: CAF management groups, one landing zone per entity plus one
shared, one subscription per environment
([ADR 0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md),
[Azure landing zones](azure-landing-zones.md)).

| Scope | Target | Status |
|---|---|---|
| Management groups | `mg-picot` hierarchy | **Gap** — not created |
| Subscriptions | `sub-picot-shared-*`, `sub-picot-dti-*` | **Gap** — everything runs in one existing company subscription |
| Shared resource group | `rg-picot-shared-data-weu` | **Coded** (`shared/` root module) |
| Entity resource group | `rg-picot-dti-data-weu` | **Deployed** under a transitional name; see [Deviations](#8-deviations-of-the-current-deployment) |
| Region | West Europe, every resource | **Deployed** |

## 3. Component inventory

| Component | Azure resource | Scope | Size / SKU | Status |
|---|---|---|---|---|
| Data lake | `stpicotdata` — StorageV2, ADLS Gen2, containers `bronze`, `silver`, `gold`, `metadata` | shared | Standard, LRS | **Deployed** |
| Entity VM | `vm-picot-dti-data-weu-01` — Ubuntu 22.04, runs Dagster, dbt, DuckDB as containers | dti | `Standard_D2s_v3`, 30 GB StandardSSD | **Deployed** |
| VM identity | `id-picot-dti-data-weu-01` — user-assigned managed identity | dti | — | **Deployed** |
| Network | `vnet-` / `snet-` / `nic-` / `pip-` / `nsg-picot-dti-data-weu-01` | dti | Standard static public IP | **Deployed** |
| Secrets | `kv-picot-dti-weu-01` — RBAC authorization | dti | Standard | **Deployed** |
| Container registry | `crpicotdtidataweu01` — admin user disabled | dti | Basic | **Deployed** |
| SAP bridge | `adf-picot-dti-data-weu-01` + `shir-picot-dti-data-weu-01` | dti | — | **Coded**, off. A portal-created factory is live in its place |
| SHIR agent host | Windows machine in the contractor's network — not an Azure resource | dti | — | **Deployed**, administered by the contractor |
| BI VM | `vm-picot-shared-bi-weu-01` — Metabase, catalog web server, refresh job | shared | Not sized | **Target** |
| Metabase databases | Postgres — application database, plus one serving database per entity ([ADR 0027](https://github.com/picot-data/data-platform-standards/blob/main/adr/0027-metabase-serves-gold-from-postgres.md)) | shared | Not sized; hosting not chosen | **Target** — H2 and DuckDB files today |
| Budgets and action groups | `modules/governance` | per resource group | — | **Coded**, not applied |
| Audit logs | Log Analytics workspace + diagnostic settings | shared | — | **Target** ([ADR 0025](https://github.com/picot-data/data-platform-standards/blob/main/adr/0025-identity-only-access-and-private-networking.md) trigger A) |
| Terraform state | Remote backend with locking and versioning | shared | — | **Target** — a local file today |

Infrastructure code: [`terraform-azure-data-platform`](https://github.com/picot-data/terraform-azure-data-platform)
(modules and the `shared/` root module) and each entity repository's
`infra/terraform/` root module
([ADR 0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md),
[ADR 0020](https://github.com/picot-data/data-platform-standards/blob/main/adr/0020-shared-scope-as-a-root-module.md)).

## 4. Network

### Addressing

Each entity VM has its own VNet with a single subnet. Every entity currently gets
the module's default address space, so **all entity VNets overlap** — harmless
while they are isolated, blocking the day any two must be peered or joined to the
corporate network. See [Open items](#open-items).

### Exposure to the internet

| Endpoint | Exposure | Control | Status |
|---|---|---|---|
| Entity VM | Public IP, port 22 only | NSG allows SSH from one admin address; key-only authentication | **Deployed** |
| Dagster UI, catalog (entity VM) | None | Bound to `127.0.0.1`; reached through an SSH tunnel | **Deployed** |
| Data lake | Public endpoint | Entra authentication; account keys still enabled | **Deployed**; keys off is **Coded** |
| Key Vault | Public endpoint | Entra RBAC | **Deployed** |
| Container registry | Public endpoint | Entra RBAC; Basic SKU cannot restrict network | **Deployed** |
| BI VM (Metabase, catalog) | HTTPS from corporate network and VPN ranges | NSG scoped to address ranges | **Target** — ranges not provided |
| Private endpoints for lake and vault | — | Replace public access | **Target** ([ADR 0025](https://github.com/picot-data/data-platform-standards/blob/main/adr/0025-identity-only-access-and-private-networking.md) trigger B) |

### Flow matrix

All Azure-bound flows are HTTPS on 443 unless stated.

| # | Source | Destination | Protocol | Authentication | Status |
|---|---|---|---|---|---|
| F1 | SHIR host | SAP system | SAP protocol, ports set by the contractor | SAP technical user | **Gap** — SAP user not yet provided |
| F2 | SHIR host | Data Factory service | HTTPS, outbound only | Runtime authorization key | **Deployed** |
| F3 | Data Factory | Lake, `bronze` | HTTPS | Factory's managed identity | **Coded**; the route from the SHIR is undecided |
| F4 | Entity VM | Lake | HTTPS | VM managed identity, Storage Blob Data Contributor | **Deployed** |
| F5 | Entity VM | Key Vault | HTTPS | VM managed identity, Secrets User | **Deployed** |
| F6 | Entity VM | Container registry | HTTPS | VM managed identity, AcrPull | **Deployed** |
| F7 | GitHub Actions | Container registry | HTTPS | OIDC federated credential, AcrPush | **Target** — needs an Entra app registration |
| F8 | GitHub Actions | Azure Resource Manager | HTTPS | OIDC, custom run-command role on the VM only | **Target**, same blocker ([ADR 0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md)) |
| F9 | Administrator | Entity VM | SSH, 22 | SSH key | **Deployed** |
| F10 | Developer workstation | Lake | HTTPS | Connection string today; Entra identity target | **Deployed**, to be replaced |
| F11 | BI VM | Lake, `gold` and `metadata` | HTTPS | BI VM managed identity, Storage Blob Data **Reader** | **Target** |
| F12 | Users | BI VM | HTTPS | Metabase accounts | **Target** |

## 5. Identity and access

| Identity | Type | Rights | Scope | Status |
|---|---|---|---|---|
| Entity VM | User-assigned managed identity | Storage Blob Data Contributor; Key Vault Secrets User; AcrPull | Lake; entity vault; entity registry | **Deployed** |
| Data Factory | System-assigned managed identity | Storage Blob Data Contributor | Lake | **Coded** |
| CI deployer | Entra app, OIDC federated credential bound to the `production` environment | AcrPush; custom role limited to `runCommand` | Entity registry; entity VM | **Target** |
| BI VM | Managed identity | Storage Blob Data Reader | Lake | **Target** |
| Platform operator | Named Entra user | Subscription Owner; Storage Blob Data Contributor; Key Vault Secrets Officer | Subscription; lake; vault | **Deployed**; an Entra group in place of the named user is **Target** |
| Metabase users | Local Metabase accounts | One Metabase database per entity | Metabase | **Target** ([BI and access](bi-and-access.md)). The open-source edition has no SSO group mapping |

No stored credential is used by any automated process except the SHIR
authorization key, held in the entity Key Vault
([ADR 0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md)).

## 6. Data

| Location | Contents | Rebuildable | Protection |
|---|---|---|---|
| Lake, `bronze` | Raw SAP extracts, append-only, all entities under `company_<code>/` | **No** | Tiered to Cool after 30 days, Archive after 365; never deleted automatically |
| Lake, `silver`, `gold` | Published dbt models | Yes, by a dbt run | Rewritten on every run |
| Lake, `metadata` | dbt docs artifacts | Yes | — |
| Entity VM disk | Bronze mirror, DuckDB build file | Yes | Transient working copy |
| Postgres serving databases | Copies of Gold, one database per entity | Yes, by the refresh | Read-only role per entity |
| Metabase application database | Users, groups, permissions, dashboards | **No** | **Gap** — no backup defined |

- **Classification.** Every resource holding SAP data is tagged
  `DataClassification = confidential`.
- **Encryption at rest.** Azure platform encryption with Microsoft-managed keys on
  the storage account and managed disks. Customer-managed keys are deliberately
  out of scope at Level 1
  ([ADR 0025](https://github.com/picot-data/data-platform-standards/blob/main/adr/0025-identity-only-access-and-private-networking.md)).
- **Encryption in transit.** HTTPS only; TLS 1.2 minimum on the lake is **Coded**.
- **Entity isolation.** By folder prefix in the lake, and by one serving
  database per entity, each with its own read-only role
  ([ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md),
  [ADR 0027](https://github.com/picot-data/data-platform-standards/blob/main/adr/0027-metabase-serves-gold-from-postgres.md)).
  In the lake the prefix is a convention: every entity VM holds Storage Blob Data
  Contributor on the whole account, so it could write under another entity's
  prefix.
- **Retention.** Raw-data retention is a business and compliance decision not yet
  taken; until it is, Bronze keeps everything.

## 7. Security, availability and operations

### Security posture

The target posture and the order in which it is reached are set by
[ADR 0025](https://github.com/picot-data/data-platform-standards/blob/main/adr/0025-identity-only-access-and-private-networking.md):
identity-only access, no public data plane, every read of the lake recorded, and
the lake protected against a single mistake.

| Measure | Status |
|---|---|
| Account keys disabled, anonymous container access forbidden | **Coded** |
| Soft delete for blobs and containers, 30 days | **Coded** |
| `CanNotDelete` lock on the lake | **Coded** |
| Blob versioning | Not available on ADLS Gen2 accounts; soft delete stands in for it ([ADR 0026](https://github.com/picot-data/data-platform-standards/blob/main/adr/0026-soft-delete-not-versioning-for-the-lake.md)) |
| Diagnostic settings to Log Analytics | **Target** |
| Remote Terraform state | **Target** |
| Private endpoints, no public IP on entity VMs | **Target** (trigger B) |
| Policy detecting a regression of this posture | **Gap** |

### Availability and recovery

| Component | Recovery | Status |
|---|---|---|
| Entity VM | Destroyed and recreated by Terraform, then redeployed from the registry image | **Deployed** |
| Lake | Single region, LRS. Soft delete and a delete lock; no second copy | **Coded** |
| Metabase application database | Not defined | **Gap** |
| Recovery objectives (RPO, RTO) | Not defined | **Gap** — a business decision |

A BI VM outage stops dashboards for every entity but loses no data: pipelines keep
publishing Gold
([ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)).

### Operations

| Activity | Mechanism | Status |
|---|---|---|
| Deployment | CI builds one platform image, pushes it to the entity registry, runs the deployment on the VM with run-command | **Target** ([ADR 0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md)) |
| Entity VM schedule | Started before the pipeline window, deallocated after, fixed daily cut-off | Cut-off **Deployed**; start and stop **Target** ([ADR 0018](https://github.com/picot-data/data-platform-standards/blob/main/adr/0018-scheduled-start-stop-for-entity-vms.md)) |
| Pipeline monitoring | Dagster UI; Data Factory monitoring for extraction | **Deployed** |
| Cost control | Budget alerts per resource group | **Coded**, not applied ([ADR 0005](https://github.com/picot-data/data-platform-standards/blob/main/adr/0005-budget-alerts-vs-automated-shutdown.md)) |
| OS patching | Not defined in code | **Gap** |
| Code quality gates | CI runs lint, `dbt parse` and the description gate on every push | **Deployed** ([Repositories and delivery](repositories-and-delivery.md)) |

## 8. Deviations of the current deployment

What runs today differs from this dossier in ways that are known and dated:

- One company subscription holds everything; no landing-zone subscriptions exist.
- The entity resource group carries a transitional `poc` name, and the lake still
  sits inside it, managed by the entity's Terraform state rather than by
  `shared/`.
- The Data Factory was created in the portal, outside Terraform and the naming
  convention. It is replaced at the production rebuild, when the SHIR is
  re-registered.
- Metabase and the catalog run on the entity VM, with H2 as the application
  database. There is no BI VM.
- Images are pulled from GitHub Container Registry, not from the entity registry.
- No budget covers the entity resource group: `modules/governance` is not
  applied. Required before production.
- Local development reaches the lake with a storage connection string, which
  stops working once account keys are disabled. The entity template's ADLS
  access and publication step move to an Entra identity before production.

## Open items

| Item | Owner |
|---|---|
| Recovery objectives (RPO, RTO) for the lake and for Metabase | Business sponsor |
| Route from the SHIR to the lake, and whether the contractor's policy requires private networking before the first extract | SAP contractor, platform owner |
| SAP technical user with table read rights | SAP contractor |
| IP plan: non-overlapping address spaces per entity, compatible with corporate ranges | Group IT, platform owner |
| Corporate and VPN address ranges allowed to reach the BI VM | Group IT |
| Metabase application database backup | Platform owner |
| OS patching policy for the VMs | Platform owner |
| Postgres hosting: a container on the BI VM or Azure Database for PostgreSQL, with a costed comparison | Platform owner |
| Who may write to Silver and Gold in production | Platform owner |
| Raw-data retention period for Bronze | Business sponsor, compliance |
