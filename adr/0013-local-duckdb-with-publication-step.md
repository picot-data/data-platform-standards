# ADR 0013: dbt materializes locally; a publication step writes Silver and Gold

**Status**: Accepted

**Date**: 2026-08-14

## Context

ADR 0001 decided *which* dbt layers are durable and *where* they live: Silver
(`stg_`) and Gold (`dim_`, `fct_`, `mart_`) on ADLS as Parquet, Intermediate
(`int_`) in the local DuckDB file only. To express that, it also named a
mechanism — dbt-duckdb's `external` materialization, which writes each model
straight to an `abfss://` path as it is built.

That mechanism failed in practice on the first entity to run it on a VM
(`poc-data-platform-dti`). With `external`, ADLS is not just where a model
*ends up*, it is where the model *lives*: every downstream `ref()` and every
dbt test re-opens that remote Parquet file. A project of eight models and
seventy tests — three mock tables' worth of data — issued several hundred
remote file operations per `dbt build`.

DuckDB's azure extension requests a fresh Entra token for each remote
operation and caches only the underlying HTTP connection, not the token. The
Azure Instance Metadata Service, which is how a VM's managed identity issues
tokens, throttles those requests at roughly five per second per VM. Tests
completing in 40 ms each blew past that ceiling, and Azure answered `429
Temporarily throttled, too many requests` on a varying subset of nodes each
run. DuckDB surfaces that as `this could mean the credentials used were
wrong`, which sent the first investigation after the credentials — they were
correct throughout.

Reducing dbt to a single thread did not help and could not: the limit is a
rate, not a concurrency, and serial execution of 40 ms nodes still exceeds it.

The underlying problem is not authentication. DuckDB is an embedded engine,
designed to work against local files. Driving the whole DAG against object
storage runs it against its own design, and the throttling is only the first
symptom to become visible — the network round-trips would have become the
binding constraint at real volumes regardless of how the platform authenticates.

## Options considered

1. **Authenticate differently, keep `external`** — a storage account key, or a
   service principal whose token endpoint is not IMDS-throttled. Unblocks the
   run in minutes, but reintroduces a long-lived shared secret to store and
   rotate, and leaves several hundred network round-trips per build in place.
   It treats the symptom.
2. **Slow dbt down to fit the rate limit** — throttle or serialise the run.
   Already tried; ineffective, and it makes build time a function of an Azure
   quota rather than of the work to be done.
3. **Keep the engine local and publish at the boundaries** — every model
   materializes as a local DuckDB table; a distinct publication step copies the
   durable ones to ADLS once per run, at the end. ADLS is read to load Bronze
   and written to publish, and touched nowhere else.

## Decision

Option 3. ADR 0001's *what* is unchanged — Bronze, Silver and Gold live on
ADLS, Intermediate does not. Only the *how* changes:

| dbt layer | Medallion layer | Materialization | Published to ADLS |
|---|---|---|---|
| — (ingestion output) | Bronze | not a dbt model | written by the ingestion pipeline |
| `stg_` | Silver | `table` (local DuckDB) | yes, by the publication step |
| `int_` | late Silver (no ADLS folder) | `table` (local DuckDB) | no |
| `dim_`, `fct_`, `mart_` | Gold | `table` (local DuckDB) | yes, by the publication step |

Which models are published is declared in dbt, not in the orchestration: a
`publish_container` entry in a model's `meta` (set per layer in
`dbt_project.yml`) names its target container. The publication step reads that
from the dbt manifest, so adding a model publishes it with no change to the
orchestration code. A model with no `publish_container` — Intermediate — stays
local, which is ADR 0001's rule expressed as configuration rather than as
convention.

The publication step is an orchestration asset, downstream of the dbt build.

## Consequences

- The durability guarantees of ADR 0001 are unchanged. A reader of that ADR
  should take its table's *Materialization* column as superseded by this one,
  and everything else in it as still current.
- dbt tests now gate publication, which `external` did not: the dbt build is a
  single orchestration step, so a failing test fails it and the downstream
  publication never runs. Nothing reaches Silver or Gold unless every test
  passed. This tightens the "no table in production without tests" commitment
  from a convention into a mechanism.
- Parallelism is available again — the VM target runs multiple threads, because
  the run no longer contends for a token-issuing quota.
- Publication is a step that can fail on its own, after a successful build.
  That is a new failure mode, and a deliberate one: it is visible and
  retryable, where a partial `external` run left some models written to ADLS
  and others not, with nothing recording which.
- Silver and Gold are refreshed once per run rather than progressively during
  it. Nothing consumes them mid-build, so this is not a regression; it does
  mean a run interrupted halfway leaves ADLS holding the *previous* run's
  output rather than a half-updated one, which is the safer of the two.
- The DuckDB file becomes load-bearing within a run — dbt writes it and the
  publication step reads it back. Both must resolve the same path, so it is
  named once in the environment and read from there by each, never hardcoded
  twice.
- Managed identity remains the authentication mechanism on the VM, with no
  stored secret. That was never the problem, and option 1 would have traded it
  away for a workaround.
- This does not scale indefinitely. It holds as long as the working set fits on
  the VM's disk, which is a Level 1 assumption consistent with ADR 0006 (a
  single VM) and ADR 0009 (plain Parquet). A Level 2 platform with a real
  distributed engine revisits this, along with much else.
