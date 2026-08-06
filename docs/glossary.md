# Glossary

Business terms are the same terms defined in the [Semantic
layer](semantic-layer.md)'s metric definitions — this page documents them in
prose; MetricFlow enforces them in code. This glossary also feeds the
DataHub business glossary once governance is wired up.

## Business terms

**Revenue** (`revenue`)
: Sum of `amount_excl_tax` across orders, defined once in dbt MetricFlow.
  Excludes tax by convention — see
  [Naming conventions — Measure columns](naming-conventions.md#measure-columns)
  for why the unit/precision is always explicit in a column name.

**Entity**
: A group company (Dirickx, and future entities). Represented in data by the
  `entity` column (`'D'`, `'B'`, ...) on every fact and dimension table — see
  [Data layers — multi-entity tables](data-layers.md#multi-entity-tables).
  Not to be confused with the Azure infrastructure `scope` code (`dti`,
  `bg`), which is a different value for the same concept — see the
  correspondence table in
  [Azure landing zones](azure-landing-zones.md#resource-naming-pattern).

## Technical terms

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

**Semantic layer**
: The layer where a business metric is defined once (in dbt MetricFlow) and
  queried consistently by every consumer, instead of being recomputed
  independently in each mart or dashboard. See [Semantic layer](semantic-layer.md).

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
