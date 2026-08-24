# Azure landing zones

Structure decided in [ADR 0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md):
a Management Group hierarchy following Microsoft's Cloud Adoption Framework
(CAF) Enterprise-Scale Landing Zone pattern, with one landing zone per entity
(plus one for group-shared resources) and three subscriptions (dev/staging/
prod) underneath each.

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/azure-landing-zones.svg"
</div>

## Subscription structure

At Level 1, only each landing zone's `prod` subscription is populated with
resources. `dev` and `staging` exist as governance scaffolding (RBAC, budget
tripwires, Terraform workspace) but stay empty — see
[Environments](#environments).

### The Platform management group

`mg-picot-platform` is the management group where, in the standard CAF model,
transverse services shared by the whole tenant would live: `Connectivity`
(VPN / ExpressRoute, hub network, central firewall), `Identity` (domain
controllers), `Management` (Log Analytics, Sentinel, Automation). It is
created as an empty placeholder — creating the management group costs
nothing and prepares the structure, exactly as `mg-picot` itself was created
holding only two subscriptions at first.

## Resource naming pattern

```
<type>-picot-<scope>-<workload>-<region>-<instance>
```

- `scope` = entity code (`dti` for Dirickx, `bg` for B&G, other codes as new
  entities arrive) or `shared` for group-wide resources
- `region` = `weu` (West Europe)
- `workload` = `data` for an entity's pipeline VM at Level 1 (everything on a
  single VM), or `bi` for the group's shared VM running Metabase — the one
  Level 1 split, because that machine serves people rather than being part of any
  entity's pipeline (see
  [ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md)).
  `bi` covers the catalog as well as the dashboards — same machine, same audience,
  same question, since "where does this number come from" is answered by walking
  from a dashboard into the catalog
  ([ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md)).
  Splits further into `compute`, `orch`, etc. at Level 2

| Resource | Name | Notes |
|---|---|---|
| Management Group (root) | `mg-picot` | |
| Management Group (platform) | `mg-picot-platform` | Out of data scope — IT-owned |
| Management Group (decommissioned) | `mg-picot-decommissioned` | Empty until needed |
| Management Group (landing zones parent) | `mg-picot-landingzones` | |
| Management Group (landing zone, shared) | `mg-picot-lz-shared` | |
| Management Group (landing zone, Dirickx) | `mg-picot-lz-dti` | |
| Management Group (landing zone, future entity) | `mg-picot-lz-<code>` | Created when the entity is onboarded |
| Subscription (shared, per env) | `sub-picot-shared-dev` / `-staging` / `-prod` | |
| Subscription (Dirickx, per env) | `sub-picot-dti-dev` / `-staging` / `-prod` | |
| Resource Group (shared, prod) | `rg-picot-shared-data-weu` | Created in `sub-picot-shared-prod`; dev/staging stay empty at Level 1 |
| Resource Group (Dirickx, prod) | `rg-picot-dti-data-weu` | Created in `sub-picot-dti-prod`; dev/staging stay empty at Level 1 |
| Storage Account (ADLS Gen2) | `stpicotdata` | 3-24 char, lowercase alphanumeric only, **global Azure uniqueness** — check availability before locking it in |
| VM (shared, BI + catalog) | `vm-picot-shared-bi-weu-01` | Runs the group's single Metabase — see [ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md) — and serves the dbt docs catalog as static files at `/catalog/<entity>/` ([ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md)). Sized for Metabase: the catalog adds a web server, not an application. Never on a start/stop schedule — it serves people during working hours, and it is the only always-on machine, which is why anything that must be reachable during the day lives here. Inbound is restricted to the corporate network and the VPN. Lives in `rg-picot-shared-data-weu` with the storage account: one shared resource group at Level 1, even though its `workload` segment differs |
| VM (Dirickx) | `vm-picot-dti-data-weu-01` | |
| Key Vault (Dirickx) | `kv-picot-dti-weu-01` | 3-24 char, global Azure uniqueness — also to be checked |
| NSG (Dirickx) | `nsg-picot-dti-data-weu-01` | |
| Virtual Network (Dirickx) | `vnet-picot-dti-data-weu-01` | One VNet per entity's VM, not shared across entities |
| Subnet (Dirickx) | `snet-picot-dti-data-weu-01` | Single subnet at Level 1 (everything on one VM) |
| Public IP (Dirickx) | `pip-picot-dti-data-weu-01` | Standard SKU |
| Network Interface (Dirickx) | `nic-picot-dti-data-weu-01` | The NSG attaches here, not on the VM resource itself |
| Managed Identity (Dirickx VM) | `id-picot-dti-data-weu-01` | The identity every process on the VM authenticates as. **User-assigned**, not system-assigned: the VM is deliberately disposable, and a system-assigned identity dies with it — every role granted to it would have to be recreated and re-propagated on each rebuild. `id-` is the CAF-standard prefix |
| Container Registry (Dirickx) | `crpicotdtidataweu01` | **No hyphens**: registry names accept only alphanumerics, so the pattern is the same segments concatenated. One registry per entity, not one shared — ACR grants `AcrPull`/`AcrPush` over a whole registry, so a shared one would let any entity's CI overwrite another entity's images ([ADR 0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md)) |
| ADLS Containers | `bronze`, `silver`, `gold`, `metadata` | No leading underscore: Azure container names accept only lowercase letters, digits and hyphens, and must start with a letter or digit |

The `entity` column in dbt tables (see
[Naming conventions](naming-conventions.md#technical-metadata-columns)) uses
this same `scope` code — one code for both data and infrastructure, not a
separate mapping to maintain.

## Environments

| Code | Meaning | Subscription |
|---|---|---|
| `prod` | Production — pipelines, real data | `sub-picot-<scope>-prod` — the only one holding active resources at Level 1 |
| `staging` | Pre-prod validation | `sub-picot-<scope>-staging` — exists (RBAC/budget ready), no resources deployed at Level 1 |
| `dev` | Development — tests, experiments | `sub-picot-<scope>-dev` — exists, but development stays local (laptop) at Level 1 |

Environments are full **subscriptions**, not resource groups within a single
subscription — required by the CAF landing zone decomposition (one
subscription per environment per landing zone). `dev` and `staging`
subscriptions are created empty so the RBAC/budget scaffolding and Terraform
workspace already exist when a real dev/staging environment becomes worth the
overhead at Level 2.

## Tagging strategy

Tags are part of the naming convention, not an afterthought. The naming
pattern above encodes identity in a string; tags encode everything the string
can't hold without becoming unreadable — cost ownership, lifecycle, data
sensitivity, who to call. A resource name answers *"what is this?"*. Tags
answer *"whose is it, what does it cost whom, and can I delete it?"*.

Tags are enforced by Azure Policy at management-group scope, not by
discipline — see
[ADR 0004](https://github.com/picot-data/data-platform-standards/blob/main/adr/0004-tagging-enforced-via-policy.md).

**Tag key casing is an exception to `snake_case`** — Azure tag keys use
`PascalCase` (`CostCenter`, `Environment`), matching Microsoft's own CAF
examples and Azure Policy built-in definitions. See
[ADR 0003](https://github.com/picot-data/data-platform-standards/blob/main/adr/0003-azure-tag-key-casing.md).
Tag *values* stay lowercase and reuse the same codes as the resource-naming
segments above (`dti`, `shared`, `prod`) — with the exception of `Owner` (an
email address) and `ExpiresOn` (a date).

### Mandatory tags

Applied to every subscription, every resource group, and every resource.

| Tag | Allowed values | Purpose |
|---|---|---|
| `Entity` | `dti` / `shared` / future entity code | Cost and ownership attribution per group entity |
| `Environment` | `dev` / `staging` / `prod` | Filtering and cost split; guard rail against pointing a dev job at prod data |
| `Workload` | `data` (Level 1) / later `compute`, `orch`, `network` | Which functional block of the platform |
| `Level` | `1` / `2` | Maturity level of the platform the resource belongs to |
| `CostCenter` | Code from Dirickx finance | Chargeback / showback to the finance analytical structure |
| `Owner` | Email of the technical owner | Who to contact before touching or deleting |
| `ManagedBy` | `terraform` / `manual` / `azure-policy` | Any resource tagged `manual` is drift from the IaC baseline |

### Recommended tags (conditional)

| Tag | Applied when | Allowed values | Purpose |
|---|---|---|---|
| `DataClassification` | Any resource holding or transiting data | `public` / `internal` / `confidential` | SAP business data is `confidential`; an internal finance dashboard is `internal`; open-data sources are `public` |
| `ExpiresOn` | Any temporary resource (POC, test, spike) | ISO date `YYYY-MM-DD` | Anti-zombie-resource. Missing this tag = the resource is permanent by declaration |
| `Project` | Everywhere it makes sense | `data-platform` / `ia-deployment` | Distinguishes data-foundation spend from IA/LLM tooling spend |
| `Criticality` | On prod resources | `low` / `medium` / `high` | Drives backup/DR expectations and on-call urgency |

### Enforcement mechanisms

| Mechanism | Azure Policy effect | What it does | Where to apply |
|---|---|---|---|
| Require the mandatory tags | `deny` | Blocks creation of a resource missing `Entity`, `Environment`, `CostCenter`, `Owner`, `ManagedBy` | `mg-picot-landingzones` |
| Inherit tags from the resource group | `modify` | Built-in policy *"Inherit a tag from the resource group"* | `mg-picot-landingzones` |
| Remediate existing resources | `modify` + remediation task | Retro-applies tags to resources created before the policy | Per subscription, one-off |

Sequencing matters: assign the `modify`/inherit policies before the `deny`
policies (see
[ADR 0004](https://github.com/picot-data/data-platform-standards/blob/main/adr/0004-tagging-enforced-via-policy.md)).

Terraform declares the mandatory tags once in a `local` block and merges them
into every resource (`tags = merge(local.common_tags, { ... })`). Never
hand-write a tag block per resource.

Management Groups themselves do **not** support Azure tags — this is a real
Azure limitation. Classification at that level is carried by the MG name and
hierarchy above, and by Azure Policy assignments, not by tags.

### Finding tagged resources

- **Cost Analysis grouped by tag**: group by `Project` to separate
  data-stack from IA spend, by `Entity` for per-entity chargeback, by `Level`
  for the Level 1 → Level 2 cost narrative.
- **Azure Resource Graph** for inventory — e.g. every resource that drifted
  from IaC:
  ```kusto
  resources
  | where tags.ManagedBy == "manual"
  | project name, type, resourceGroup, tags.Owner
  ```
  or every resource past its expiry date:
  ```kusto
  resources
  | where isnotempty(tags.ExpiresOn) and todatetime(tags.ExpiresOn) < now()
  | project name, type, resourceGroup, tags.Owner, tags.ExpiresOn
  ```
- **Alert routing**: budget and monitoring alerts resolve their recipient
  from the `Owner` tag rather than from a hardcoded email list.

## Cost control — budgets and limits

**Azure Cost Management budgets are a notification mechanism, not a spending
cap.** Reaching 100% of a budget sends an alert and changes nothing else —
the resources keep running and the bill keeps growing. No resource group is
created without a budget covering it, from the first `terraform apply`.

The *spending limit* feature that hard-stops a subscription only exists on
credit-based offers (free trial, Visual Studio/MSDN) — not on Enterprise
Agreement or Microsoft Customer Agreement subscriptions.

Cost control is therefore two distinct layers:

| Layer | Mechanism | What it actually does |
|---|---|---|
| Detect | Cost Management budget + alerts | Emails at thresholds. Does not stop anything |
| Act | Budget → Action Group → Automation runbook | Actually deallocates the VM or removes write permissions |

Layer 1 (detect) is implemented everywhere, systematically. Layer 2 (act) is
implemented only where it's worth the cost — see
[ADR 0005](https://github.com/picot-data/data-platform-standards/blob/main/adr/0005-budget-alerts-vs-automated-shutdown.md).

### Budget structure

Budgets are set at three nested scopes, each catching a different failure
mode:

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/budget-structure.svg"
</div>

| Scope | Failure mode it catches |
|---|---|
| `mg-picot-landingzones` | Total drift across all entities — the number defended in CODIR |
| Each `prod` subscription | One entity's platform becoming disproportionately expensive |
| Each `dev` / `staging` subscription | Someone spins up a resource "just to test" and forgets it |
| Each resource group | A specific workload misbehaving inside an otherwise healthy subscription |

### Alert thresholds

| Threshold | Type | Recipient |
|---|---|---|
| 50% | Actual | Owner |
| 80% | Actual | Owner |
| 100% | Actual | Owner + finance contact |
| 110% | Actual | Owner + finance + manager |
| 100% | Forecast | Owner |

The forecast-100% alert warns before the money is spent, based on the
current trend — configure it on every budget. Alert recipients are defined
via an Action Group, not a raw email list, so routing can be changed in one
place.

### Hard limits

| Guard rail | Mechanism | Where |
|---|---|---|
| Entity VM started before its pipeline window | Scheduled GitHub Actions workflow running `az vm start`, over the existing OIDC federation | Entity VMs only. Scheduled an hour ahead, because GitHub's cron is best-effort and can be delayed |
| Entity VM deallocated when the run finishes | Last step of the Dagster pipeline, using the VM identity's rights on its own resource | Entity VMs only. A **failed** run deliberately leaves the VM up, to be inspected |
| Entity VM cut off at a fixed hour regardless | Azure VM auto-shutdown schedule | Entity VMs only. The backstop for a failed run: without it, a failure on the first day of a holiday bills weeks of idle compute |
| Deallocate the VM at 110% of budget | Budget alert → Action Group → Automation runbook | `dev`/`staging` only — see ADR 0005 |
| Storage lifecycle policy on `bronze` | ADLS lifecycle management (hot → cool → archive) | Bronze — raw files never re-read after a few weeks |
| Resource-type restriction | Azure Policy `deny` on expensive SKUs | Dev subscriptions |
| Azure Advisor cost recommendations | Reviewed monthly | All subscriptions |

### Everything in Terraform

Budgets, action groups, and policy assignments are infrastructure, so they
live in the same Terraform code as the rest of the platform, in a dedicated
`governance/` module — applied per subscription from the same `.tfvars` as
everything else. A budget created by hand in the portal will not exist on the
next entity's subscription.

## Operating rules

- Every resource must carry its mandatory tags before creation, and every
  resource group needs a budget covering it — flag any Terraform snippet or
  portal action that would create one without the other.
- Never present an Azure budget as a spending *limit*; it is an alert. A
  genuine hard stop requires the automation layer, which trades cost for
  availability.
- Do not invent budget amounts, cost-center codes, or Azure prices — see
  [open questions](https://github.com/picot-data/data-platform-standards/issues?q=is%3Aissue+is%3Aopen+label%3Aopen-question).
- When onboarding a new entity, apply the same template documented here
  rather than improvising — see
  [Onboarding a new entity](onboardings/onboarding-a-new-entity.md).
