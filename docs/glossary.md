# Glossary

Business terms are the same terms defined in the
[metric definitions](semantic-layer.md) — this page documents them in prose,
the `mart_` models compute them in SQL. This glossary also feeds the
DataHub business glossary once governance is wired up.

## Business terms

**Revenue** (`revenue`)
: Sum of `amount_excl_tax` across orders, defined once in a `mart_` model.
  Excludes tax by convention — see
  [Naming conventions — Measure columns](naming-conventions.md#measure-columns)
  for why the unit/precision is always explicit in a column name.

**Entity**
: A group company (Dirickx, B&G, and future entities). Represented in data
  by the `entity` column (`'dti'` = Dirickx, `'bg'` = B&G, ...) on every fact
  and dimension table — see
  [Data layers — multi-entity tables](data-layers.md#multi-entity-tables).
  The same code is also used for the Azure infrastructure `scope` segment in
  resource names — one code, not two — see
  [Azure landing zones](azure-landing-zones.md#resource-naming-pattern).

## Technical terms

**Level 1 / Level 2**
: The platform's maturity ladder. Level 1 is the current scope of every page
  on this site: one VM per entity, plain Parquet, no dev/staging resources
  beyond empty governance scaffolding — everything needed to prove the
  pipeline end to end at POC scale. Level 2 is the not-yet-designed next
  step (splitting the single VM into per-component compute, a managed
  catalog, etc.) referenced as a placeholder in tags and naming patterns —
  see [Platform overview](platform-overview.md) and
  [Azure landing zones — Resource naming pattern](azure-landing-zones.md#resource-naming-pattern).

**CAF (Cloud Adoption Framework)**
: Microsoft's Enterprise-Scale Landing Zone pattern, adopted for the
  management group and subscription hierarchy — see
  [Azure landing zones](azure-landing-zones.md) and
  [ADR 0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md).

**Medallion architecture**
: The bronze/silver/gold refinement model for data storage — describes *how
  refined and how durable* data is. Orthogonal to the dbt model layers below.
  See [Data layers](data-layers.md).

**dbt model layers** (staging, intermediate, dimensions, facts, marts)
: Describe *what kind of SQL transformation* produced a model — orthogonal to
  the medallion architecture above. See [Data layers](data-layers.md).

**Surrogate key** (`_sk` suffix)
: A generated technical key (via `dbt_utils.generate_surrogate_key`), used to
  join facts to dimensions, as opposed to a natural key (`_id` suffix) that
  carries business meaning from the source system. See
  [Naming conventions — Identity columns](naming-conventions.md#identity-columns-keys).

**Metric definition**
: The single place a business metric is computed — a `mart_` model — instead of
  being recomputed independently in each dashboard. See
  [Metric definitions](semantic-layer.md).

**Semantic layer**
: A tool that resolves a metric definition at query time, so any consumer asking
  for it at any grain gets the same answer. The platform does *not* run one:
  [ADR 0015](https://github.com/picot-data/data-platform-standards/blob/main/adr/0015-metrics-in-marts-not-metricflow.md)
  records why dbt MetricFlow was dropped in favour of marts.

**Star schema**
: A modeling pattern (Kimball) where a fact table's measures are described by
  surrounding dimension tables, joined by keys — as opposed to flat,
  pre-aggregated marts built directly from staging. See
  [Data layers — Why a star schema](data-layers.md#why-a-star-schema-not-marts-built-directly-from-staging).

**Landing zone**
: In the Cloud Adoption Framework, a management group + set of subscriptions
  dedicated to one workload boundary — here, one per group entity. See
  [Azure landing zones](azure-landing-zones.md) and
  [ADR 0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md).

**ADR (Architecture Decision Record)**
: An immutable record of one decision — context, options considered,
  consequences — kept separate from the reference docs. See the
  [ADR index](adr-index.md).
