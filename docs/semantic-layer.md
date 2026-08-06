# Semantic layer

## The problem a semantic layer solves

Without a semantic layer, a metric like revenue tends to get computed
independently in several places: once in a dbt mart, once in a Metabase
question, once in a spreadsheet someone builds for a meeting. Each
computation makes its own small, reasonable-looking choice — include tax or
not, count cancelled orders or not — and the three numbers quietly diverge.
Nobody notices until two people bring different "revenue" figures to the same
meeting.

**A metric is defined once, centrally, in dbt MetricFlow — never recomputed
independently in a mart or in the BI tool.** Every consumer of that metric,
whether a dbt mart, a Metabase dashboard, or an ad hoc query, resolves back to
the same definition.

## Where metrics are defined

Metrics are defined in `transformation/metrics/`, on top of the Gold star
schema — never on top of staging or intermediate models. A metric definition
references:

- a **semantic model**, which maps a fact table (e.g. `fct_order`) to its
  measures, dimensions, and entities;
- one or more **measures**, the aggregation of a column (e.g. `sum` of
  `amount_excl_tax`);
- optionally, a **filter**, when the metric represents a subset (e.g.
  revenue excluding cancelled orders).

```yaml
# transformation/metrics/fct_order.yml (illustrative)
semantic_models:
  - name: fct_order
    model: ref('fct_order')
    entities:
      - name: order
        type: primary
    dimensions:
      - name: date_order
        type: time
        type_params:
          time_granularity: day
    measures:
      - name: revenue_excl_tax
        agg: sum
        expr: amount_excl_tax

metrics:
  - name: revenue
    type: simple
    type_params:
      measure: revenue_excl_tax
```

The metric name follows the naming pattern in
[Naming conventions](naming-conventions.md#dbt-model-naming) — no prefix, just
the business term (`revenue`, not `mart_revenue` or `fct_revenue`).

## Querying a metric

MetricFlow resolves a metric query into SQL against the underlying Gold
tables, at whatever dimension and time grain is requested — a BI tool query
for "revenue by month" and one for "revenue by customer" both resolve to the
same `revenue` definition, just grouped differently. This is what makes the
single-definition guarantee real: it is not a discipline the team has to
maintain by convention, it is what happens mechanically when a metric is
queried through MetricFlow instead of hand-written in a dashboard.

## What this proves

A dashboard that reads "chiffre d'affaires: 1.2M€" should be traceable back
to one metric definition, one semantic model, one fact table — not to a
`SUM()` written independently inside a Metabase question. This is the same
traceability argument that motivates the [governance and lineage
catalog](platform-overview.md#governance-datahub): if someone in finance asks
"where does this number come from", the answer is a metric definition anyone
can open, not something only one person remembers.
