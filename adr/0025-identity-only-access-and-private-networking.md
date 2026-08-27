# ADR 0025: Identity-only authentication and private networking, on two named triggers

**Status**: Accepted

**Date**: 2026-08-27

## Context

A third-party contractor who maintains the group's SAP systems and their
servers reviewed the platform's Azure footprint on 2026-08-27, ahead of the
ingestion work in [ADR 0010](0010-adf-not-python-scripts-for-sap.md). Their
summary was that it is fine for a proof of concept and not production-ready,
and they raised public storage access and unspecified "Azure prerequisites".

The reaction was not the finding. The finding is that **no page in this
repository says what the platform's security posture is**, so there was nothing
to answer with. Networking, authentication and auditability appear nowhere:
[Azure landing zones](../docs/azure-landing-zones.md) covers naming, tagging and
cost, and stops there. Every choice below was made silently, and from outside
the team a silent choice and an oversight are indistinguishable.

### What is actually deployed

Read from `terraform-azure-data-platform` at `v2.1.0` and the entity repository's
`infra/terraform/main.tf`. Nothing here is anonymous access, and no incident is
known — this is exposure, not a breach.

| Property | Today | Why it is what it is |
|---|---|---|
| Storage data plane | Reachable from any IP. `modules/storage` sets neither `network_rules` nor `public_network_access_enabled`, so the provider default applies | Never decided |
| Container access | `private` on all four containers, so nothing is readable anonymously | Decided |
| `allow_nested_items_to_be_public` | Unset, therefore `true` on azurerm 3.x — a container *can* be flipped to public by mistake | Never decided |
| `shared_access_key_enabled` | Unset, therefore `true`. A connection string lives in a developer `.env`, documented in the entity repo's `main.tf` | Accepted as a workaround: DuckDB's azure extension cannot invoke `az` on Windows |
| Blob recoverability | No soft delete, no versioning, LRS, no resource lock — on the one asset in the stack that cannot be rebuilt | Never decided |
| Key Vault | RBAC authorization on; no network ACLs; purge protection off | RBAC and purge protection decided; the network path never was |
| VM ingress | Static public IP; NSG allows only port 22 from `admin_source_cidr`; password authentication disabled | Decided |
| Data-plane audit trail | None. No diagnostic settings, no Log Analytics workspace — there is no record of who read what | Never decided |
| Terraform state | A local file on one laptop, holding secrets in clear | Decided, for the POC |
| Human data access | `Storage Blob Data Contributor` granted directly to the operator's own account | Never decided |

Four rows in that table are genuine decisions with reasoning behind them. Six
are defaults nobody chose. That ratio is the problem this ADR exists to close.

### Why the deferral matters more here than on a normal POC

The platform owner's standing decision is that the POC *is* production at reduced
scale: real resource names from day one, no rename and no rebuild at handover,
with the `Environment` tag as the only marker of the transition. That decision is
sound and is not reopened here, but it has a consequence that was never written
down — **there is no clean reset.** Hardening will happen in place, on the
resource that already holds data, with no throwaway scope to practise on. Doing
it while the lake holds mock fixtures is a Terraform change; doing it after real
SAP extracts land is a migration.

### Why the timing is not ours to choose

The self-hosted integration runtime of ADR 0010 runs inside the contractor's
network. Their own policy is therefore applied to the destination it writes to,
and a corporate policy forbidding writes to a publicly-reachable storage
endpoint is common. Private networking may not be a production improvement at
all: it may be a **precondition of the ingestion project**, held by someone
outside this team. That is the likely content of "Azure prerequisites", and it is
tracked as an open question — which of the contractor's points are their landing
zone's policy and which are general advice — rather than guessed at here.

## Options considered

1. **Harden everything now**, before further feature work. Removes the exposure
   at once, and spends the POC's remaining weeks — with a steering-committee
   review in early September — on infrastructure rather than on the pipeline the
   review is about.
2. **Leave it, and deal with it at the production handover.** Cheapest today, and
   it is precisely the shape of deferral this ADR was written because it already
   failed once: undocumented, unscheduled, indistinguishable from an oversight,
   and by then applied to a lake holding real data.
3. **Rebuild a hardened stack under throwaway names and migrate.** Gives a clean
   practice ground, and reverses the owner's decision above at the cost of the
   globally-unique storage account name it exists to protect.
4. **Stage the work on two named triggers**, chosen so that each item is done at
   the last moment it is still cheap.

## Decision

Option 4. Two triggers, each with a fixed scope. Neither is a date, because both
depend on events the team does not fully control.

**The target posture, stated once so it can be checked:** access to data is
granted to an Entra identity and never to a key; the data plane is reachable
from the platform's own network and not from the internet; every read of the lake
leaves a record; and the one non-rebuildable resource cannot be destroyed by a
single mistake.

### Trigger A — before the first real SAP extract lands in `bronze`

Everything on this list is a Terraform change, needs nothing from the
contractor, and becomes materially harder once the container holds business data.

- `shared_access_key_enabled = false` and
  `allow_nested_items_to_be_public = false` on the storage account.
- Blob soft delete and versioning enabled; a `CanNotDelete` lock on the account.
- Diagnostic settings on the storage account and the Key Vault, to a Log
  Analytics workspace.
- Terraform state moved to a remote backend with locking and versioning.
- The operator's data-plane role assignment replaced by an Entra group.

**One precondition, not a consequence to discover afterwards.** Disabling account
keys breaks anything still holding a connection string. Since
[ADR 0013](0013-local-duckdb-with-publication-step.md) moved dbt onto a local
Bronze mirror, DuckDB makes no Azure call during a build, so the `.env`
connection string is very likely already dead weight — but that is verified
before the flag flips, not after.

### Trigger B — with the ADF and SHIR workstream

- Private endpoints for the storage account and the Key Vault, with their private
  DNS zones, and `public_network_access_enabled = false` on both.
- The entity VM loses its public IP; administrative access moves to the private
  path or to Azure Bastion.
- The route from the contractor's SHIR to the lake is decided explicitly and
  written down, rather than defaulting to the public endpoint because it works.

Bundled with the ingestion work rather than scheduled before it, because the
contractor's requirements shape the topology and doing this twice is the only
way to waste it.

### Out of scope at Level 1, deliberately

Microsoft Defender for Storage, customer-managed encryption keys,
geo-redundant replication, a hub-and-spoke topology with Azure Firewall, and
ExpressRoute. Named so that their absence reads as a decision. Each is revisited
when the platform has a stakeholder asking for it — the test
[ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md) applied to DataHub, which
is why none of them is on a trigger above.

## Consequences

- **The `Environment` tag can no longer flip on its own.** The owner's transition
  marker is a tag change; this ADR makes trigger A and trigger B preconditions of
  that change. A resource tagged `prod` while its account keys are live
  misrepresents the platform in the one place designed to describe it
  ([ADR 0003](0003-azure-tag-key-casing.md),
  [ADR 0004](0004-tagging-enforced-via-policy.md)).
- **Trigger B breaks local development, and that is the item most likely to be
  underestimated.** With `public_network_access_enabled = false`, a developer
  laptop is not on the VNet and loses access to ADLS — including the publication
  step of ADR 0013, which runs locally today. Three ways out: a VPN into the
  VNet, an IP exception in the storage firewall, or publication moving to the VM
  only. The choice belongs to trigger B's design and must be made there, not
  found at apply time.
- **Private endpoints are billed per hour and per gigabyte processed.** Price them
  on the Azure calculator before applying; nothing here should be assumed free.
- **Nothing detects a regression of this posture.** A future `terraform apply`
  that drops a flag plans cleanly and applies silently. Azure Policy is the
  mechanism already trusted for tags, and the same `deny` shape — no storage
  account with public network access, no storage account with shared keys
  enabled — is what turns this ADR from a document into a control. Until that
  exists, this posture holds by review only.
- **Auditability becomes answerable for the first time.** The traceability claim
  made for the catalog — that the provenance of a figure can be shown by clicking
  rather than recalled by a person — currently stops at the dbt lineage
  ([ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md)). Diagnostic settings
  extend it to who read the underlying data, which is the second question an
  auditor asks.
- **The contractor's review stands as accepted, not disputed.** Their conclusion
  was correct on the substance. What this ADR rejects is only the reading that
  the posture was never considered, and it rejects it by writing the posture
  down — which was not possible before today.
- Revisited if the contractor's policy turns out to forbid connecting the SHIR at
  all until private networking exists, in which case trigger B moves ahead of
  trigger A and the ingestion timeline absorbs it; or if group IT provides a hub
  network or ExpressRoute, which would replace the per-entity topology assumed
  throughout [ADR 0002](0002-caf-landing-zone-structure.md).
