# ADR 0009: Plain Parquet at Level 1, not Iceberg or Delta

**Status**: Accepted

**Date**: 2026-07-30

## Context

Every layer of the Gold and Silver data (see
[ADR 0001](0001-medallion-dbt-layer-persistence.md)) needs a file format on
ADLS. Table formats like Iceberg or Delta add time travel and schema
evolution on top of Parquet, and had already been experimented with in an
earlier POC.

## Options considered

1. **Iceberg or Delta** — excellent long-term properties (time travel, schema
   evolution), but at Level 1 they add a catalog to maintain; a
   PyIceberg + SQLite catalog in particular is fragile to run in anything
   resembling production.
2. **Plain Parquet** — no catalog, no extra moving part. DuckDB reads it
   natively.

## Decision

Option 2. Plain Parquet for Bronze, Silver, and Gold at Level 1.

## Consequences

- No time travel or schema evolution at the storage layer — replay and
  history rely on Bronze's immutable date partitions and dbt snapshots (see
  [Naming conventions — Archiving](../docs/naming-conventions.md#archiving)),
  not on the table format.
- The migration cost to a table format later is close to zero: Parquet files
  are already the underlying format Iceberg and Delta build on. Level 2's
  managed platform (e.g. Databricks with Unity Catalog) can adopt Iceberg or
  Delta natively without rewriting the Level 1 data, only re-registering it.
