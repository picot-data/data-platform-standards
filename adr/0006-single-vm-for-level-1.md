# ADR 0006: A single VM for all Level 1 tools, per entity

**Status**: Accepted

**Date**: 2026-07-30

## Context

Level 1 needs to run ingestion scripts, an orchestrator, a transformation
tool, and a query engine somewhere. A choice was needed between one VM per
tool, one VM per entity running everything, or something else.

## Options considered

1. **One VM per tool** (ingestion, orchestration, transformation each on
   their own machine) — clean separation, but multiplies cost, patching
   surface, and network complexity for tools that are individually
   lightweight.
2. **One VM per entity, running every tool** — DuckDB is an embedded engine
   (one file, no server), dbt Core is a Python CLI, Dagster OSS is a
   lightweight web service. None of these justify their own machine at
   Level 1 volumes.
3. **One VM shared across entities** — cheapest, but an entity's compute then
   depends on another entity's subscription, breaking the per-entity billing
   and access boundary that the landing zone structure (ADR 0002) is built
   around.

## Decision

Option 2. One VM per entity (`vm-picot-<code>-data-weu-01`), running every
Level 1 tool. Not one VM per tool, not one VM shared across entities.

## Consequences

- The bottleneck at Level 1 is not compute — it's access to source data (SAP)
  and the Owner's time. Splitting compute across machines would not remove
  that bottleneck.
- Moving to multiple machines/services happens naturally at Level 2 with a
  managed platform (e.g. Databricks): the tools change, not the pipeline
  logic. dbt code stays the same (adapter change); Dagster pipelines stay the
  same (compute target change).
- This decision is revisited only if a single tool's resource usage on its
  own threatens to saturate the VM — see ADR 0007 for exactly this concern
  with ingestion tooling.
