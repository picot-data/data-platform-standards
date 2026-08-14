# ADR 0015: Metric definitions live in dbt marts, not in MetricFlow

**Status**: Accepted

**Date**: 2026-08-14

## Context

The roadmap chose dbt MetricFlow as the semantic layer, for one reason: a
metric like revenue should be defined **once**, so a dbt model, a BI dashboard
and an ad hoc query cannot quietly produce three different numbers.

That guarantee is not a property of *writing* a metric in MetricFlow. It is a
property of *querying through* MetricFlow — the definition only binds a
consumer that asks MetricFlow to resolve it.

That is where the plan breaks. In dbt Core, MetricFlow is queried through its
CLI. The BI integrations that make a semantic layer useful — Looker, Tableau,
Hex, Mode — go through the **dbt Cloud** Semantic Layer API, which is a paid
platform this project does not use. Metabase has no native integration with
either, and has had an open feature request for it since 2022.

So today, `revenue` defined in `transformation/metrics/` is invisible to
Metabase. Someone building a dashboard would write `SUM(amount_excl_tax)` in a
Metabase question — the exact duplication MetricFlow was adopted to prevent.
The platform carries the cost of the tool (a second modelling language, a
second mental model, semantic models to maintain) while getting none of its
central benefit.

This was not foreseeable from the tool comparison that chose MetricFlow: it is
a fact about the *combination* of dbt Core and Metabase, not about either tool.

## Options considered

1. **Adopt dbt Cloud** — makes the Semantic Layer API available and the original
   plan real. It also introduces a paid platform and a second orchestration
   surface next to Dagster, for one capability.
2. **Keep MetricFlow for CLI use, define metrics again in Metabase** — the worst
   of both: the duplication is still there, and a tool is maintained on top of
   it. The single-definition guarantee becomes a claim rather than a fact.
3. **Define metrics in dbt marts, and expose those marts to Metabase** — the
   definition lives in SQL, in one reviewed place, and reaches the BI tool
   because the BI tool reads tables.

## Decision

Option 3. Metrics are defined in `mart_` models. MetricFlow, and the
`transformation/metrics/` directory, are dropped.

The single-definition rule survives the change of mechanism and is **not**
relaxed — it changes from something enforced by a tool to something enforced by
review:

- Metric logic lives **only** in `mart_` models. A `SUM`, a ratio or a filter
  that encodes a business definition never appears in a Metabase question.
- A mart **never stores a ratio or an average**. It stores the numerator and
  the denominator, and the BI tool divides. Storing `average_order_value`
  directly makes it impossible to aggregate correctly — the average of daily
  averages is not the average over the period.
- Marts are built at the **finest grain that is useful**, and only *additive*
  measures (sums, counts of rows) may be rolled up by the BI tool. A
  `COUNT(DISTINCT ...)` is not additive and must be exposed at each grain it is
  needed at, or derived from a mart holding the distinct keys.
- Every metric mart carries a description and dbt tests, like any other model.

## What is given up

| | MetricFlow | Metrics in marts |
|---|---|---|
| Reaches Metabase | **No** (needs dbt Cloud's API) | **Yes** — it is a table |
| One definition, mechanically enforced | Yes, for consumers that query it | No — enforced by convention and review |
| Any grain from one definition | Yes, resolved per query | No — grains are chosen when the mart is built |
| Non-additive measures (distinct counts) | Recomputed correctly per grain | Manual: expose per grain, or store the keys |
| Ratios and derived metrics | Composed safely per grain | Manual: store numerator + denominator |
| Multi-fact queries without double counting | Handled | Manual care in the SQL |
| Cumulative / period-over-period | Built in | Written by hand |
| Skills needed to read a definition | MetricFlow YAML | SQL |
| Tooling to maintain | A semantic layer | None beyond dbt |

The honest summary: MetricFlow's real value is **correctness under
re-aggregation** — it stops a reader from summing something that must not be
summed. Marts move that responsibility onto whoever writes them. Three of the
rules in the Decision above exist specifically to contain that risk.

## Consequences

- The metric a dashboard shows is now traceable to a `mart_` model, not to a
  metric definition. Still one artefact, still in Git, still reviewed — the
  traceability argument to a steering committee is unchanged.
- **The existing definitions must be migrated with care, not translated
  mechanically.** Of the three metrics defined today: `revenue` is a plain sum
  and is additive; `order_count` is a `COUNT(DISTINCT order_id)` and is *not*
  additive unless every line of an order shares one `date_order`, which has to
  be verified rather than assumed; `average_order_value` is a ratio and must
  never be stored as a column.
- A new grain now costs a model change instead of a query parameter. At Level 1
  volumes that is a small, visible cost — and it is the cost of the tools
  actually in use talking to each other.
- If the group ever adopts dbt Cloud, or Metabase ships a semantic layer
  integration, this is worth revisiting: the decision follows from a tooling
  gap, not from a belief that semantic layers are unnecessary. That would be a
  new ADR.
- Nothing about the Gold star schema changes. Dimensions and facts remain the
  source of truth and remain exposed for self-service; marts remain commodities
  built on top — they simply gain metric definitions as an explicit job.
