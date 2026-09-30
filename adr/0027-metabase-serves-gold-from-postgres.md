# ADR 0027: Metabase reads Gold from Postgres, not from DuckDB files

**Status**: Accepted — supersedes the serving engine of ADR 0016

**Date**: 2026-09-30

## Context

[ADR 0016](0016-central-metabase-not-per-entity.md) put one Metabase on the
shared BI VM. A scheduled refresh pulls each entity's Gold Parquet from the lake
and rebuilds **one serving DuckDB file per entity**, holding views over the local
Parquet. That ADR also required the Metabase application database — users,
groups, permissions, dashboards — to move from H2 to **Postgres** before the
instance serves the group.

So the BI VM will run Postgres whatever is decided here. The question is whether
the serving copies should live in it too, rather than in DuckDB files next to it.
Four facts bear on it:

- **The DuckDB driver is a community plugin.** Metabase does not ship it
  ([ADR 0008](0008-metabase-not-power-bi.md) accepted it as one more
  dependency). It follows Metabase releases with a delay, so every Metabase
  upgrade waits on it, and ADR 0017 already had to work around capabilities it
  could not verify. Postgres is one of Metabase's own drivers.
- **A DuckDB file has one writer and blocks it against readers.** The refresh
  rebuilds files that Metabase has open. That forces either a file swap timed
  around open connections, or a refresh that fails when a dashboard is being
  read.
- **Entity isolation rests on Metabase's configuration alone.** One serving
  database per entity is the permission boundary (ADR 0016), but every DuckDB
  file is readable by the one Metabase process. The files carry no credential of
  their own, so nothing below Metabase enforces the boundary.
- **Concurrency is the likeliest trigger of [ADR 0014](0014-duckdb-scale-ceiling.md).**
  It sets "more than two concurrent consumers of the serving copy" as a reopening
  signal. A group-wide Metabase used by several controllers at once is exactly
  that, well before any volume signal.

## Options considered

1. **Keep one DuckDB file per entity** (ADR 0016 as written). No load step, and
   columnar performance. Keeps the community driver, the writer lock and the
   Metabase-only boundary.
2. **Postgres for the serving copies, in the same instance as the application
   database, one database per entity.** One official driver, transactional
   refresh, a database role per entity. Adds a load step.
3. **A separate Postgres instance for serving.** Isolates the dashboards'
   query load from the application database. A second stateful service to run,
   size and patch, for a load Level 1 does not have.
4. **Metabase queries the lake directly** through a query engine. Brings back the
   remote-read throttling ADR 0013 and ADR 0016 exist to avoid, or a new
   service to run.

## Decision

Option 2. Metabase reads Gold from Postgres, in the same instance that holds its
application database.

- **One Postgres database per entity**, keeping the Metabase database names of
  [BI and access](../docs/bi-and-access.md) (`gold_dti`, `gold_bg`, …). Each has
  its own **read-only role**, used by exactly one Metabase connection. The
  application database is a separate database with its own role.
- **The refresh stays a pull on a schedule** (ADR 0016, unchanged). For each
  entity it loads the Gold Parquet into a staging schema of that entity's
  database, using DuckDB's `postgres` extension, then swaps the staging schema
  for the live one in a single transaction.
- **Where Postgres runs is not decided here.** A container on the BI VM and
  Azure Database for PostgreSQL are both compatible with this decision. The
  choice is made when the BI VM is built, with a costed comparison. Either way,
  the application database needs a backup.

Everything else in ADR 0016 stands: one central Metabase, the pull model, one
database per entity as the permission grain, and Postgres as the application
database.

## Consequences

- **Metabase upgrades stop depending on a community plugin.** The DuckDB driver
  leaves the Metabase image.
- **A refresh no longer competes with readers.** Dashboards read the previous
  data until the swap commits; a failed load leaves the previous data in place
  rather than a half-written file.
- **Isolation is enforced twice.** Metabase permissions decide who sees which
  database; the database role decides what each connection can read. A
  misconfigured Metabase grant can still expose an entity's data. What becomes
  impossible is a connection reaching another entity's tables.
- **The serving copy becomes tables, not views over Parquet.** It was already a
  copy that lags the pipeline by one refresh interval (ADR 0016); nothing about
  freshness changes. The load step can fail on a DuckDB type Postgres lacks, and
  it must fail loudly rather than coerce silently.
- **Row storage is slower than DuckDB on large scans.** Gold is the layer that
  stays small (ADR 0014), so this is not expected to matter at Level 1. Slow
  dashboards are the signal to measure before adding indexes or reconsidering the
  engine.
- **Postgres takes memory on the BI VM**, which has to be counted when the
  machine is sized.
- **ADR 0017 is unchanged.** Loaded tables could carry constraints, but Metabase
  still seeds descriptions from the database only once, so the API route remains
  the only one that keeps Metabase in step with dbt.
- **The POC is not changed.** It keeps its serving DuckDB until the BI VM is
  built. [BI and access](../docs/bi-and-access.md),
  [Platform overview](../docs/platform-overview.md) and
  [Onboarding a new entity](../docs/onboardings/onboarding-a-new-entity.md) still
  describe DuckDB serving files and must be brought in line.
- Revisited if dashboard latency on Postgres becomes a measured problem that
  indexing does not solve, or if an entity's data may no longer share an
  instance with another's (the condition ADR 0016 already names).

## References

- [Metabase — supported databases](https://www.metabase.com/docs/latest/databases/connecting)
- [Metabase — application database](https://www.metabase.com/docs/latest/installation-and-operation/configuring-application-database)
- [DuckDB — PostgreSQL extension](https://duckdb.org/docs/stable/core_extensions/postgres)
