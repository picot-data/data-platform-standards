# ADR 0001: Persistence strategy per medallion / dbt layer

**Status**: Accepted

**Date**: 2026-07-30

## Context

The dbt layer naming (staging, intermediate, dimensions, facts, marts) and the
medallion storage naming (bronze, silver, gold) were both defined, but nothing
stated which dbt layer is physically persisted, where, and in what
materialization. Without that rule, the same model could reasonably end up as
a throwaway view or as a Parquet file in the lake, decided ad hoc per model.

## Options considered

1. **Persist every layer to ADLS** — maximum durability, but wasteful: `int_`
   models are pure scaffolding, fully derivable from Silver in one `dbt build`.
2. **Persist nothing except Gold, rebuild everything else on demand** —
   cheapest, but makes every rebuild dependent on the SAP extraction being
   available and fast, which it currently is not.
3. **Persist by durability need, not by convenience** — Bronze immutable and
   never touched by dbt; Silver persisted to ADLS because the SAP extraction
   behind it is slow and IT-dependent; Intermediate kept only inside the local
   DuckDB file since it is disposable scaffolding; Gold persisted to ADLS
   because it is the consumed product.

## Decision

Option 3. Concretely:

| dbt layer | Medallion layer | Materialization | Physically lives in |
|---|---|---|---|
| — (ingestion output) | Bronze | not a dbt model | ADLS `bronze/` (date-partitioned, immutable) |
| `stg_` | Silver | `external` (Parquet) | ADLS `silver/` |
| `int_` | late Silver (no ADLS folder) | `table` | DuckDB file on the VM only |
| `dim_`, `fct_`, `mart_` | Gold | `external` (Parquet) | ADLS `gold/` |

## Consequences

- Losing the DuckDB file when the VM is destroyed is acceptable by design: it
  holds nothing that a `dbt build` cannot recompute from Silver.
- Every downstream rebuild becomes independent of SAP availability once Silver
  exists, at the cost of some storage for an intermediate copy of the data.
- `stg_` and `int_` models need no backup strategy.
- Two related items are open, not decided by this ADR: whether dimensions
  need history (a dbt snapshot on staging) if the business needs "what was
  this customer called when the order was placed", and how `_loaded_at`
  should be defined once Bronze is wired to a real ingestion pipeline. Both
  are tracked as open questions rather than assumed either way.
- Incremental models are deliberately deferred: at Level 1 volumes, a full
  rebuild of every layer is simpler and safer than incremental logic (unique
  keys, late-arriving rows, reprocessing windows). Revisit when a full
  `dbt build` becomes painful, not before.
