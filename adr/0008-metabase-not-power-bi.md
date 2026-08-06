# ADR 0008: Metabase, not Power BI, as the BI tool

**Status**: Accepted

**Date**: 2026-08-05

## Context

An earlier version of the architecture document named Power BI as the
consumption layer for the Gold data. Power BI is not actually deployed or
licensed at Dirickx, and adopting it would introduce a new licensing
dependency on top of everything else Level 1 needs to prove.

## Options considered

1. **Power BI** — familiar in a Microsoft shop, but not currently deployed at
   Dirickx; adopting it means acquiring and managing licenses before the POC
   can even connect a dashboard.
2. **Metabase** — open-source, self-hosted, no license to acquire, connects to
   DuckDB via a community driver (`metabase-duckdb-driver`).

## Decision

Option 2. Metabase, self-hosted on the same VM as the rest of Level 1.

## Consequences

- Metabase does not read Parquet files directly — DuckDB does the reading,
  Metabase talks to DuckDB through its community driver. This is one more
  moving part than a native DirectQuery connector would be, but it avoids a
  licensing dependency entirely.
- DuckDB allows one writer at a time. If Metabase queries the file while a
  `dbt build` is writing to it, the query can be blocked or fail — mitigated
  by scheduling `dbt build` outside expected dashboard usage hours.
- If the group later standardizes on Power BI for other reasons (e.g. an
  existing enterprise agreement), that is a new decision, not an extension of
  this one — the DuckDB/Parquet Gold layer underneath does not change either
  way.
