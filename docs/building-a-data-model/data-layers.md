# Data layers

Two different axes describe a dbt model, and conflating them is the most
common source of confusion for anyone new to this project: the **medallion
architecture** describes *how refined and how durable* the data is, while the
**dbt model layers** describe *what kind of SQL transformation* produced it.
A model has exactly one position on each axis.

## The two axes

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/data-layers.svg"
</div>

Bronze is not a dbt model at all — it's the ingestion pipeline's raw output,
read-only for dbt. Silver corresponds to `stg_` models. Intermediate (`int_`)
models sit *inside* Silver conceptually (further cleansing/joining) but are
not persisted to ADLS at all — see below. Gold corresponds to `dim_`, `fct_`,
and `mart_` models. This mapping, and exactly where each layer is physically
stored, is decided in
[ADR 0001](https://github.com/picot-data/data-platform-standards/blob/main/adr/0001-medallion-dbt-layer-persistence.md).

How the data gets there is a separate question, decided in
[ADR 0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md):
dbt builds every model as a table in a **local** DuckDB file, and a publication
step copies the durable ones to ADLS once, at the end of the run. DuckDB is an
embedded engine — it reads and writes local files, and the platform touches
object storage only at the two edges of a run (load Bronze, publish Silver and
Gold).

## The dbt layers, in transformation order

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/dbt-transformation-order.svg"
</div>

| Layer | What it does | What it must never do |
|---|---|---|
| **Staging** (`stg_`) | One-to-one with a source object: renaming, retyping, light cleansing | No joins, no aggregation. A `stg_` model that needs a join is an `int_` model |
| **Intermediate** (`int_`) | Joins and enrichments that don't yet belong to a specific dimension or fact | Producing something ready for a BI tool — that's Gold's job |
| **Dimensions** (`dim_`) | Descriptive attributes of a business entity (customer, product, date) | Holding measures or business-process facts |
| **Facts** (`fct_`) | Measurable events of a business process (an order, a delivery) | Duplicating dimension attributes instead of referencing them by key |
| **Marts** (`mart_`) | Pre-aggregated, domain-specific views for a recurring or complex analysis | Being the source of truth — dimensions and facts are; marts are a commodity built on top of them |

## Persistence per layer

Each dbt layer has a fixed materialization and storage location, defined in
[ADR 0001](https://github.com/picot-data/data-platform-standards/blob/main/adr/0001-medallion-dbt-layer-persistence.md)
and refined by
[ADR 0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md):

| dbt layer | Medallion layer | Materialization | Ends up in |
|---|---|---|---|
| — (ingestion output) | Bronze | not a dbt model — written by the ingestion pipeline, read-only for dbt | ADLS `bronze/` (date-partitioned, immutable) |
| `stg_` | Silver | `table` (local DuckDB) | ADLS `silver/`, via the publication step |
| `int_` | late Silver (no ADLS folder) | `table` (local DuckDB) | DuckDB file on the VM only — never published |
| `dim_`, `fct_`, `mart_` | Gold | `table` (local DuckDB) | ADLS `gold/`, via the publication step |

**Every model materializes locally.** dbt never writes to `abfss://` — a
publication step copies the durable models out at the end of the run, one
Parquet file per model. Which ones get published is declared in dbt itself, as
a `publish_container` entry in the model's `meta`, set per layer in
`dbt_project.yml`:

```yaml
models:
  <project>:
    staging:
      +materialized: table
      +meta:
        publish_container: silver
    intermediate:
      +materialized: table      # no publish_container: stays local
    dimensions:
      +materialized: table
      +meta:
        publish_container: gold
```

Do **not** reintroduce dbt-duckdb's `external` materialization to write models
straight to ADLS. It makes every downstream `ref()` and every test re-open a
remote file, and the resulting flood of Entra token requests hits the instance
metadata service's rate limit — surfacing as `429 Temporarily throttled`,
reported by DuckDB as a credentials error that it is not. ADR 0013 has the full
account.

## Archiving

Persistence and archiving are different questions. Only three needs carry an
archiving obligation:

| Need | Where it is answered |
|---|---|
| Rebuild a past state / prove where a figure came from | Bronze — immutable, date-partitioned raw extracts |
| Keep the history of a business change (a customer renamed, a price revised) | dbt snapshots (`snapshots/`, `dbt snapshot`) |
| Reduce the cost of old raw files | ADLS lifecycle rules (hot → cool → archive) on `bronze/` |

`stg_` and `int_` models are not archived: they are fully derivable from
Bronze. Restoring them is a `dbt build`, not a restore from backup.

## Why a star schema, not marts built directly from staging

Building `mart_monthly_revenue` directly from staging models (skipping
dimensions and facts) works for a single question, but every *new* question
then means a new mart built from scratch, with its own copy of the same join
logic:

| Direct marts from staging | Star schema (dimensions + facts) |
|---|---|
| Each new question = a new mart from scratch | Each new question = a mart that joins the same dimensions/facts |
| "Sales by product category" → new model, new logic | "Sales by product category" → `SELECT` on `fct_order JOIN dim_product` |
| No self-service — everything is pre-aggregated | BI users can freely explore dimensions and facts |
| Adding a dimension means rewriting every mart | Adding a dimension means one new `dim_` table plus one key in the fact table |

Marts do not disappear in a star schema — they become the pre-aggregated
layer for recurring or complex analyses (e.g. a monthly finance dashboard, or
a cross-source analysis combining Gold data with an external source). The
rule that follows from this: **dimensions and facts are the source of truth;
marts are commodities** built on top of them, never the other way around.

## Multi-entity tables

Every fact and dimension table carries an `entity` column (`'dti'` = Dirickx,
`'bg'` = B&G, etc.) rather than one table per entity. When a new entity's
data lands in `fct_order`, it arrives as additional rows with a new `entity`
value in the same table. Same table, same structure, no duplication.

**The column is the data model, not the access control.** It is what lets one set
of models serve every entity and one query compare them. What an entity is
*allowed* to see is enforced one level down, at the serving database Metabase
connects to: `gold_dti` holds Dirickx's rows, `gold_group` holds everyone's, and a
group tied to one of them cannot reach the other. Metabase's open-source edition
has no row or column security — filtering on `entity` inside a query is a
convention, and a convention is not a boundary. See
[BI and access — Data permissions](../bi-and-access.md#data-permissions) for what
actually holds the line.

See
[Naming conventions](../naming-conventions.md#technical-metadata-columns) for the
column definition, and
[Azure landing zones](../azure-landing-zones.md#resource-naming-pattern) for how
this same code is used for the Azure infra `scope` segment in resource
names.
