# ADR 0014: When a single DuckDB node stops being the right engine

**Status**: Accepted

**Date**: 2026-08-14

## Context

ADR 0006 put every Level 1 tool on one VM per entity, and ADR 0013 made that
VM's DuckDB the place where all transformation happens. Both are sound at
current volumes. Neither says at what point they stop being sound.

That silence is the problem. "Will DuckDB hold?" is a question that gets asked
repeatedly, answered by intuition each time, and only settles when something
breaks in front of an audience. It deserves observable criteria decided while
nothing is on fire.

Two facts frame the answer:

- **DuckDB's ceiling is much higher than its reputation suggests.** It handles
  billions of rows on a single machine given selective predicates and
  partitioning, and the practical guidance is that if compressed data fits on
  available disk with memory to spare for working subsets, a single node is
  likely enough. Single servers now reach hundreds of cores and a terabyte of
  RAM, so "scale up" is a long runway, not a last resort.
- **The ceiling is workload-shaped, not size-shaped.** The same row count
  behaves very differently depending on the query. Window functions are the
  known early casualty: they become worth watching around 30M rows and cross a
  minute around 50M on commodity hardware, while filtered aggregations over the
  same table stay fast.

The entity VMs are currently `Standard_D4s_v3` — 4 vCPU, 16 GB — which is small
by the standards of that research. Thresholds below are calibrated to that size,
not to a large server.

## Options considered

1. **No stated limit** — revisit when something is slow. Cheapest now, and
   guarantees the decision is made under pressure, with a stakeholder waiting.
2. **A single row-count threshold** — easy to state, and wrong: it ignores that
   query shape, not table size, is what actually degrades.
3. **A set of observable signals, with an escalation ladder** — several
   independent measurements, none of which alone forces a change, plus an
   explicit order of remedies to try before changing engine.

## Decision

Option 3. A single DuckDB node remains the engine while all of the following
hold. **Two of them breaking at once is what reopens the decision** — any one
alone is a tuning problem, not an architecture problem.

| Signal | Stay | Watch | Reopen |
|---|---|---|---|
| Rows in the largest fact table | < 20M | 20M–50M | > 50M |
| Full `dbt build` wall time | < 10 min | 10–30 min | > 30 min |
| Working set (Parquet, compressed) vs VM disk | < 25% | 25–50% | > 50% |
| Concurrent consumers of the serving copy | 1 | 2 | > 2 |

The row-count band is deliberately conservative against the published figures:
those describe well-provisioned hardware, and 4 vCPU / 16 GB is not that. The
concurrency signal is the one most likely to trigger first, and the least
related to volume — see the consequences.

**Reopening the decision does not mean adopting a distributed engine.** The
remedies are tried in this order, and the next one is only reached when the
previous is exhausted:

1. **Scale the VM up.** Changing `vm_size` in the entity's `.tfvars` is a
   one-line change (ADR 0006 anticipated it), and the hardware headroom above
   `D4s_v3` is enormous. This is almost always the correct first answer, and it
   is frequently the last one needed.
2. **Make the expensive models incremental.** ADR 0001 deferred incremental
   models on purpose; a full rebuild becoming the bottleneck is exactly the
   condition it named for revisiting them. This addresses build time without
   touching the architecture.
3. **Separate the serving copy from the build.** Already true for Metabase
   (ADR 0013). Extending it — more serving copies, or a serving node distinct
   from the build node — buys concurrency without a new engine.
4. **Only then, a different engine.** A warehouse or a distributed compute
   layer, at which point ADR 0006 and ADR 0013 are both back on the table.

## Consequences

- The question "will this hold?" now has an answer that can be measured rather
  than argued. The measurements should be taken periodically, not only when
  something feels slow — a build time trending from 4 to 9 minutes is
  information, and it is invisible if nobody looks.
- **Concurrency, not volume, is the likeliest trigger, and it is not a matter of
  growth.** A single DuckDB file serves one process. A second BI tool, an
  export job, or a group-level consolidation reading several entities' Gold all
  arrive as *organisational* changes, not as data growth, and any of them can
  cross the line while the tables are still small. Planning for scale by
  watching row counts alone would miss it entirely.
- Gold is not the layer to watch. Dimensions are bounded by their business
  entities and fact tables are narrow, so Gold stays small for a long time.
  Bronze is what grows without bound, and it is a storage-cost question handled
  by lifecycle tiering, not an engine question.
- Choosing "scale up" repeatedly has a cost this ADR does not hide: a larger VM
  is billed continuously, and at some point a warehouse that scales to zero
  between runs is cheaper than a permanently large machine. That crossover is a
  finance question and is not decided here.
- The thresholds are estimates calibrated to today's hardware and workload. They
  are meant to be revised when measured behaviour contradicts them — a
  superseding ADR, not a silent edit.

## Sources

- [The Practical Limits of DuckDB on Commodity Hardware](https://dev.to/prithwish_nath/the-practical-limits-of-duckdb-on-commodity-hardware-f76)
- [DuckDB Performance: Querying Large Datasets on a Single Machine](https://motherduck.com/duckdb-book-summary-chapter10/)
- [Scaling DuckDB: A Modern Architecture for Analytical Data Applications](https://medium.com/@tanejagagan/scaling-duckdb-a-modern-architecture-for-analytical-data-applications-49e5a8dcd24a)
