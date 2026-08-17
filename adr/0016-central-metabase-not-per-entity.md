# ADR 0016: One central Metabase for the group, not one per entity

**Status**: Accepted

**Date**: 2026-08-17

## Context

[ADR 0006](0006-single-vm-for-level-1.md) put every Level 1 tool on one VM per
entity, and Metabase was included in that list without being examined on its
own. The reasoning behind ADR 0006 is about *compute*: an entity's pipeline
should not depend on another entity's subscription, because the landing zone
structure ([ADR 0002](0002-caf-landing-zone-structure.md)) makes the
subscription the billing and access boundary.

Metabase is not compute. It is a consumption surface, and consumption is where
the group-level question is asked. Three facts made the per-entity placement
untenable once the first Metabase was actually in use:

1. **The group view is the point.** The platform exists to analyse the group's
   sales. [Data layers](../docs/data-layers.md) states this explicitly: a
   group-level dashboard filters `entity IN ('dti', 'bg')`. With one Metabase
   per entity, each instance sees only its own entity's Gold folder, and that
   dashboard cannot exist anywhere.

2. **Per-entity instances multiply the configuration, not the data.** Table
   metadata, foreign keys, collections, groups, users and dashboards would be
   configured N times, and would drift between instances. There is no shared
   layer to hold a definition once — the opposite of the property every other
   part of the platform is built for.

3. **The audience is not per entity.** A group controller compares entities;
   an entity controller looks at one. With N instances the first person needs
   N logins and cannot compare anything, while the second gains nothing from
   the isolation.

The immediate objection is access: if one Metabase sees every entity's Gold,
what stops a Dirickx user from reading B&G's figures? That objection is what
shaped the decision rather than blocking it — see
[Consequences](#consequences) and
[BI and access](../docs/bi-and-access.md#data-permissions).

## Options considered

1. **One Metabase per entity, on the entity VM** — the status quo implied by
   ADR 0006. Isolation is a property of the architecture and needs no
   configuration. But no group-level dashboard is possible, and every piece of
   BI configuration is duplicated per entity and drifts.
2. **One Metabase per entity, plus a group instance** — restores the group
   view, and makes the duplication worse: N+1 instances, and the group instance
   still needs access to every entity's data, so the isolation argument for the
   others is already conceded.
3. **One central Metabase in the shared landing zone** — one instance, on a VM
   in `sub-picot-shared-prod` next to the storage account it reads. Isolation
   between entities becomes a permissions problem instead of a topology
   property, which is a problem that has to be solved deliberately and can then
   be audited in one place.

## Decision

Option 3. Metabase runs once for the whole group, on
`vm-picot-shared-bi-weu-01` in `rg-picot-shared-data-weu`, and is removed
from the per-entity VM's tool list.

ADR 0006 is **not** reversed: one VM per entity still runs every tool of the
ingestion-to-Gold pipeline (Dagster, dbt Core, DuckDB, ingestion scripts).
Only the consumption layer moves. A reader of ADR 0006 should take its list of
tools as excluding Metabase from this date; everything else in it stands.

### How the data reaches it

The central Metabase reads Gold from ADLS, but **not directly**. A scheduled
refresh on the BI VM pulls the published Gold Parquet files to local disk and
rebuilds one serving DuckDB database per scope:

| Metabase database | Built from | Who may see it |
|---|---|---|
| `gold_dti` | `gold/company_dti/*.parquet` | Dirickx groups, group analysts |
| `gold_bg` | `gold/company_bg/*.parquet` | B&G groups, group analysts |
| `gold_group` | every `gold/company_*/` folder, unioned | group analysts only |

Keeping the engine on local files rather than pointing DuckDB at `abfss://` is
the same rule [ADR 0013](0013-local-duckdb-with-publication-step.md) arrived at
for dbt, for the same reason: DuckDB is an embedded engine and requests a fresh
Entra token per remote operation. A dashboard refreshing on every page view
would reproduce exactly the throttling that ADR 0013 exists to avoid. The pull
itself is a handful of file reads per refresh, which is well inside the limit.

**One serving database per entity is a permissions mechanism, not a
convenience.** [Data layers](../docs/data-layers.md#multi-entity-tables) says
entity scoping is expressed as a filter on the `entity` column — and a filter
is exactly what Metabase's open-source edition cannot enforce, because row and
column security is a paid feature. Metabase's finest free-of-charge grain is
the database. Splitting the serving copy per entity therefore turns a
convention that a user could bypass into a boundary they cannot, without
buying a licence.

### Why a pull, not a push

The refresh runs on the BI VM on a schedule, rather than being triggered by
each entity's Dagster run at the end of publication.

- A push means every entity's orchestration needs network and credentials into
  the shared subscription — N couplings across a boundary the landing zone
  structure exists to keep clean.
- `gold_group` unions every entity. On a push model, whichever entity ran last
  would rebuild it, so a database covering the whole group would be owned by
  whichever pipeline happened to finish — and would silently go stale for an
  entity that stopped running.

The cost is freshness: Metabase lags the pipeline by up to one refresh
interval. Every dashboard carries the `_loaded_at` of its underlying data so
that the lag is visible rather than assumed.

## Consequences

- **Entity isolation is now configuration, and configuration can be wrong.**
  This is the real price of the decision. It is contained by two rules, both in
  [BI and access](../docs/bi-and-access.md): the `All Users` group is stripped
  of data access before anything else is granted, and each entity's serving
  database is a separate Metabase database so that the grant is a single
  switch. Both are auditable on one screen, which N instances never were.
- **The application database must move from H2 to Postgres.** H2 on a volume
  was defensible for one entity's POC instance; it is not for the one system
  holding the group's users, permissions and dashboards. Metabase's own
  documentation treats H2 as unsuitable beyond trials, and the migration path
  is documented and one-way.
- **Metabase leaves `bootstrap_vm.sh`** for entity VMs, and the BI VM gets its
  own bootstrap. See
  [Onboarding a new entity](../docs/onboarding-a-new-entity.md).
- **The shared landing zone gains its first compute.** Until now
  `sub-picot-shared-prod` held only the storage account. It now holds a VM,
  which means the shared root module calls a new `modules/bi` alongside
  `modules/storage`, and the shared subscription needs its own budget line —
  it stops being a storage-only cost.
- **The naming convention gains a `bi` workload segment.** Level 1 used
  `workload = data` everywhere on the grounds that everything ran on one VM per
  entity. That premise no longer holds for this machine, and calling it
  `vm-picot-shared-data-weu-01` would hide the single most important thing about
  it. `bi` is therefore added as an allowed value in
  [Azure landing zones](../docs/azure-landing-zones.md#resource-naming-pattern).
  The resource *group* stays `rg-picot-shared-data-weu`: there is one shared
  resource group at Level 1, and splitting it for one VM would buy nothing.
- **Entity VMs can now be deallocated outside pipeline hours.** They no longer
  serve dashboards, so nothing needs them awake during business hours — which
  removes the blocker the
  [hard-limits table](../docs/azure-landing-zones.md#hard-limits) records
  against VM auto-shutdown. It also means they can be sized for a batch window
  rather than for interactive querying. Acting on either is a separate decision
  with its own availability trade-off, not a consequence to apply silently.
- **A single point of failure for consumption.** If the BI VM is down, no
  entity has dashboards, where before an outage was contained to one entity.
  Accepted: the pipeline keeps running and Gold keeps being published, so the
  outage costs visibility for its duration and no data.
- **Onboarding an entity gains a BI step** — two groups, one collection tree,
  one serving database — and loses a Metabase installation. Net less work per
  entity, which is the direction ADR 0011 pushes everything.
- This is revisited if an entity ever requires that its data not be
  co-resident with another entity's under any access model — a legal or
  contractual constraint, not a preference. That would be a new ADR, and the
  answer would probably be a second instance rather than a return to N.
