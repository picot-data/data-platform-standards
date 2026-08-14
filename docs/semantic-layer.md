# Metric definitions

## The problem this solves

Without a single place to define them, a metric like revenue tends to get
computed independently in several places: once in a dbt mart, once in a
Metabase question, once in a spreadsheet someone builds for a meeting. Each
computation makes its own small, reasonable-looking choice — include tax or
not, count cancelled orders or not — and the three numbers quietly diverge.
Nobody notices until two people bring different "revenue" figures to the same
meeting.

**A metric is defined once, in a `mart_` model, and never recomputed in the BI
tool.**

This used to be dbt MetricFlow's job. It is not, any more:
[ADR 0015](https://github.com/picot-data/data-platform-standards/blob/main/adr/0015-metrics-in-marts-not-metricflow.md)
records why. In short, MetricFlow only binds a consumer that *queries through*
it, and in dbt Core it is reachable from a CLI — the BI integrations run
through dbt Cloud's paid Semantic Layer API, and Metabase has no integration
with either. A metric defined in MetricFlow was therefore invisible to the only
BI tool in the platform, which is the one place it needed to be visible.

## Where metrics are defined

In `transformation/models/marts/`, on top of the Gold star schema — never on
top of staging or intermediate models. The mart is the metric: it computes it,
documents it, and is what Metabase reads.

The metric name follows the naming pattern in
[Naming conventions](naming-conventions.md#dbt-model-naming): a mart is
`mart_<domain>__<analysis>`, and the metric it carries is the business term
itself (`revenue`, not `revenue_calc`).

## Three rules that make this safe

Moving metrics out of a semantic layer moves the responsibility for correct
re-aggregation onto whoever writes the mart. These three rules contain that,
and they are not stylistic:

**1. Never store a ratio or an average.** Store the numerator and the
denominator, and let the BI tool divide. The average of daily averages is not
the average over the period, and a stored `average_order_value` column cannot
be aggregated to a month without being wrong.

```sql
-- mart_sales__daily_orders
select
    date_day,
    entity,
    sum(amount_excl_tax) as revenue,      -- numerator
    count(distinct order_id) as order_count  -- denominator
from ...
group by 1, 2
```

Metabase then shows average order value as `revenue / order_count`, computed
over whatever period the user selected.

**2. Only additive measures may be rolled up.** Sums and row counts add up
across periods; `COUNT(DISTINCT ...)` does not, unless the distinct key cannot
appear in two periods. Verify that assumption rather than inheriting it — an
order whose lines span two dates breaks it silently, and the total is simply
too high with nothing to indicate it.

**3. Metric logic never appears in a Metabase question.** A `SUM` in a saved
question is a second definition, and the fact that it usually agrees with the
mart is what makes the day it disagrees so hard to find.

## Self-service and marts are not alternatives

Exposing only marts would make Metabase a viewer: every new question becomes a
modelling ticket. Exposing dimensions and facts is what makes it a self-service
tool — see [Data layers](data-layers.md#why-a-star-schema-not-marts-built-directly-from-staging).

Both are exposed, and they answer different needs:

| | Dimensions + facts | Marts |
|---|---|---|
| For | Exploring a question nobody anticipated | A recurring or complex analysis |
| Requires | Knowing which tables to join | Nothing |
| Holds a metric definition | No — raw measures | Yes |
| Changes when | The business model changes | A new recurring question appears |

Rule of thumb: a question asked once is a Metabase query over facts and
dimensions. A question asked every month, or one whose logic is subtle enough
that two analysts would get different answers, becomes a mart.

## What this proves

A dashboard reading "chiffre d'affaires: 1.2M€" is traceable to one `mart_`
model in Git, reviewed and tested — not to a `SUM()` written inside a Metabase
question that only its author remembers. If someone in finance asks where the
number comes from, the answer is a file anyone can open.
