# ADR 0007: In-house Python ingestion scripts, not Airbyte OSS

**Status**: Partially superseded by [ADR 0010](0010-adf-not-python-scripts-for-sap.md)
for SAP ingestion specifically — still governs ingestion of non-SAP sources

**Date**: 2026-07-30

## Context

Level 1 runs every tool on a single, deliberately small VM (ADR 0006). An
ingestion mechanism was needed for SAP and other sources, and it has to fit
on that VM alongside Dagster, dbt, and DuckDB.

## Options considered

1. **Airbyte OSS** — a mature connector ecosystem, but it runs via Docker and
   consumes roughly 4-6 GB of RAM. On a VM already shared with Dagster and
   dbt, that is enough to make things tight, and it has caused concrete
   problems in a previous POC.
2. **In-house Python extraction scripts** — lighter, fully controlled, and
   sufficient for a limited number of sources (SAP plus a few APIs).

## Decision

Option 2. Python scripts, not Airbyte, at Level 1.

## Consequences

- Every new source is a new script, reviewed and versioned like any other
  code — there is no connector marketplace to rely on, so building each
  extraction is the team's own work.
- Airbyte becomes worth reconsidering only if the number of connectors grows
  large enough that hand-writing each one stops being the cheaper option —
  not a mandate to adopt it at any particular threshold, just the condition
  under which this decision would need revisiting.
