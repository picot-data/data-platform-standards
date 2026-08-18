# ADR 0019: DataHub joins Metabase on the shared VM, on one machine rather than two

**Status**: Superseded by ADR-0021

**Date**: 2026-08-17

## Context

[ADR 0016](0016-central-metabase-not-per-entity.md) moved Metabase to a shared
VM and, in doing so, exposed that the same reasoning had never been applied to
DataHub. DataHub was on the entity VM for one reason only:
[ADR 0006](0006-single-vm-for-level-1.md) put *every* Level 1 tool there, and
the tools were never examined one at a time. That was defensible when there was
one entity. It is not a decision anyone made about DataHub.

Every argument from ADR 0016 transfers without modification, and one is
stronger:

- **A catalog is group-wide by definition.** Its job is to answer "what data
  exists and where does this figure come from". Split per entity, it answers
  that question per entity, and the group-level lineage — the thing that makes
  the answer credible to a steering committee — cannot exist anywhere.
- **The glossary is the worst thing to duplicate.** A business definition of
  revenue held in N catalogues is N definitions. The platform's central claim
  is that a metric is defined once
  ([ADR 0015](0015-metrics-in-marts-not-metricflow.md)); a per-entity glossary
  contradicts it in the very tool meant to publish it.
- **It is the one thing that keeps entity VMs awake.** DataHub is a
  continuously running set of containers serving a UI. As long as it sits on the
  entity VM, that VM cannot be deallocated outside pipeline hours — see
  [ADR 0018](0018-scheduled-start-stop-for-entity-vms.md). Metabase leaving
  alone would not have unlocked that; DataHub is the binding constraint.

The one real argument for keeping DataHub next to the pipeline is that it
ingests dbt's `manifest.json` and `catalog.json`, which are produced on the
entity VM. That is a file transfer, not a colocation requirement — and the
group already has a container for exactly this: `metadata`, created alongside
`bronze`/`silver`/`gold` and until now unused.

That settles *where*. It leaves *how many machines*: one VM hosting both
Metabase and DataHub, or one each.

## Options considered

1. **Keep DataHub on each entity VM** — the status quo. N catalogues, no group
   lineage, a duplicated glossary, and entity VMs that can never sleep.
2. **A shared VM for Metabase and a second shared VM for DataHub** — isolates a
   heavy, multi-container application from an interactive one. Also doubles the
   OS disks, the patching surface, the network resources, the monitoring and the
   Terraform to maintain, for two services with a combined audience of a handful
   of people.
3. **One shared VM hosting both** — a single machine sized for the sum, with
   memory limits on DataHub's containers so it cannot starve Metabase.

## Decision

Option 3. DataHub and Metabase both run on `vm-picot-shared-bi-weu-01`, and
DataHub is removed from the entity bootstrap.

DataHub ingests from the `metadata` container on ADLS: the entity pipeline
publishes `manifest.json` and `catalog.json` there at the end of a run, and the
shared VM ingests from there on a schedule. This mirrors what
[ADR 0013](0013-local-duckdb-with-publication-step.md) already does for Silver
and Gold — the entity writes to storage, the consumer reads from storage, and
neither reaches into the other's machine.

**Why one VM and not two.** This is ADR 0006's own reasoning applied one level
up: splitting compute across machines multiplies cost and operational surface
without removing any bottleneck, and the bottleneck at Level 1 is the Owner's
time. Two VMs would mean two of everything to provision, patch, monitor and
explain, to separate two services used by the same people for the same purpose.

**Why that argument does not fully apply, and what replaces it.** ADR 0006's
premise was that the tools are *individually lightweight*. DataHub is not: it
runs a metadata store, a search index and several services, and
[ADR 0007](0007-python-scripts-not-airbyte.md) already established that a
memory-hungry container stack sharing a VM is a real failure mode, from
experience. The premise is therefore replaced by an explicit control rather than
waved away:

- The VM is sized for DataHub's documented requirements **plus** Metabase, not
  for their average.
- DataHub's containers carry explicit memory limits, so that a search index
  growing unexpectedly degrades DataHub and does not take the dashboards with
  it.
- If those limits turn out to be the thing constantly in the way, splitting the
  machine is a compose file change and a Terraform module call — cheap, and
  reversible in the direction that costs least to discover late.

**The workload segment stays `bi`.** DataHub is a catalog rather than a BI tool,
so the name is a slight stretch. It is kept anyway: the audience, the session
and the question are the same — "where does this number come from" is answered
by walking from a dashboard into the catalog — and a third rename of this
machine in one sitting would cost more in confusion than the name saves in
precision.

## Consequences

- **Entity VMs become genuinely small and genuinely disposable.** What remains
  is Dagster, dbt Core, DuckDB and the ingestion scripts: a batch workload that
  can be sized for its window and switched off outside it. This is the
  precondition for ADR 0018, and the real prize of both this ADR and 0016.
- **The `metadata` container gets its first use**, and the publication step
  gains a second job: publishing the dbt artifacts, not only the data. Small
  change, and it puts the artifacts somewhere durable rather than only on a
  disposable VM.
- **Lineage becomes group-wide**, which is what makes it worth showing to a
  steering committee. Cross-entity lineage was not previously possible.
- **The shared VM becomes a real single point of failure**, now for both
  dashboards and the catalog. Neither is on the critical path of the pipeline:
  an outage costs visibility for its duration and no data, and Gold keeps being
  published throughout.
- **The shared VM needs sizing and a budget commensurate with DataHub**, which
  is the heaviest component of the stack. The shared subscription's budget line,
  new as of ADR 0016, has to reflect that rather than a storage-plus-small-VM
  assumption.
- **Onboarding an entity loses a DataHub installation** and gains nothing: the
  new entity's dbt artifacts land in the `metadata` container and the existing
  catalog picks them up. Combined with ADR 0016, an entity's bootstrap is now
  the pipeline and nothing else.
- **Ingestion is scheduled, so the catalog lags the pipeline**, exactly as the
  BI serving copy does. Acceptable for a catalog, where the question asked is
  about structure and provenance rather than about today's figures.
- Revisited if DataHub's resource use makes the shared VM unstable in practice
  despite the memory limits — in which case the answer is option 2, a second
  machine, not a return to one per entity.
