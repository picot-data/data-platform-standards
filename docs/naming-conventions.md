# Naming conventions

**Scope**: the entire data foundation — ingestion, transformation, storage,
BI, git. Applicable to every group entity.

**Core principle**: anyone unfamiliar with the project should be able to read
a table or column name and understand what it is, where it comes from, and
which layer it belongs to.

## General rules

All rules below apply everywhere: tables, columns, files, cloud resources.

| Rule | Good example | Bad example |
|---|---|---|
| `snake_case` everywhere, no exceptions | `amount_excl_tax` | `AmountExclTax`, `amount-excl-tax`, `Amount Excl Tax` |
| English for all objects | `revenue` | `chiffre_affaires` |
| No ambiguous abbreviations — if abbreviated, it must be documented (see [Allowed abbreviations](#allowed-abbreviations)) | `qty` | `q`, `qt` |
| No accents or special characters | `order_number` | `numéro_commande` |
| No redundant prefixes with the schema/folder | `dim_customer.name` | `dim_customer.customer_name` |
| Singular table names (dbt convention) | `dim_customer` | `dim_customers` |

Azure tags are the one deliberate, documented exception to `snake_case` — see
[Azure landing zones](azure-landing-zones.md#tagging-strategy).

## dbt model naming

### Layer pattern

| Layer | Prefix | Pattern | Example |
|---|---|---|---|
| Source (declaration) | — | `_<source>__sources.yml` | `_sap__sources.yml` |
| Staging (Silver) | `stg_` | `stg_<source>__<object>` | `stg_sap__order` |
| Intermediate | `int_` | `int_<description>` | `int_order_enriched` |
| Dimension (Gold) | `dim_` | `dim_<business_entity>` | `dim_customer` |
| Fact (Gold) | `fct_` | `fct_<business_process>` | `fct_order` |
| Mart (Gold) | `mart_` | `mart_<domain>__<analysis>` | `mart_finance__monthly_revenue` |
| Metric (MetricFlow) | — | `<metric_name>` | `revenue` |

The double underscore `__` is a semantic separator: it separates the object's
origin (source) or the analysis domain. **Source names** reflect the
originating system, not the content — `stg_sap__order`, not `stg_sales__order`,
so that a future `stg_ebiz__order` from a different system stays
distinguishable. **Domain names** in marts reflect the business organization
(`finance`, `production`, `quality`, `sales`, `hr`). If a mart crosses multiple
domains, choose the primary one and document it in the dbt description.

Keep staging thin: no joins, no aggregation. A `stg_` model that needs a join
is an `int_` model.

### Persistence per layer

Each dbt layer has a fixed materialization and storage location, defined in
[ADR 0001](https://github.com/picot-data/data-platform-standards/blob/main/adr/0001-medallion-dbt-layer-persistence.md):

| dbt layer | Medallion layer | Materialization | Physically lives in |
|---|---|---|---|
| — (ingestion output) | Bronze | not a dbt model — written by the ingestion pipeline, read-only for dbt | ADLS `bronze/` (date-partitioned, immutable) |
| `stg_` | Silver | `external` (Parquet) | ADLS `silver/` |
| `int_` | late Silver (no ADLS folder) | `table` | DuckDB file on the VM only |
| `dim_`, `fct_`, `mart_` | Gold | `external` (Parquet) | ADLS `gold/` |

### Archiving

Persistence and archiving are different questions. Only three needs carry an
archiving obligation:

| Need | Where it is answered |
|---|---|
| Rebuild a past state / prove where a figure came from | Bronze — immutable, date-partitioned raw extracts |
| Keep the history of a business change (a customer renamed, a price revised) | dbt snapshots (`snapshots/`, `dbt snapshot`) |
| Reduce the cost of old raw files | ADLS lifecycle rules (hot → cool → archive) on `bronze/` |

`stg_` and `int_` models are not archived: they are fully derivable from
Bronze. Restoring them is a `dbt build`, not a restore from backup.

## Column naming

### Identity columns (keys)

| Type | Pattern | Example | Notes |
|---|---|---|---|
| Natural primary key | `<object>_id` | `order_id`, `customer_id` | Identifier from the source system |
| Surrogate key | `<object>_sk` | `order_sk`, `customer_sk` | Generated key (hash), used in facts |
| Foreign key | `<referenced_object>_id` or `_sk` | `customer_id` in `fct_order` | Same name as the referenced dimension's PK |

The `_sk` suffix indicates a generated technical key (via
`dbt_utils.generate_surrogate_key`), not a business identifier. `_id` keys are
identifiers with business meaning (SAP order number, customer code, etc.).

### Measure columns

| Type | Pattern | Example |
|---|---|---|
| Amount | `amount_<precision>` | `amount_excl_tax`, `amount_incl_tax`, `amount_tax` |
| Quantity | `qty_<object>` | `qty_ordered`, `qty_delivered`, `qty_scrap` |
| Rate / ratio | `rate_<object>` | `rate_scrap`, `rate_margin` |
| Weight | `weight_<unit>` | `weight_kg` |
| Duration | `duration_<unit>` | `duration_min`, `duration_days` |

The unit is part of the column name when it's not obvious. `amount_excl_tax`
is in the default currency documented in the [glossary](glossary.md).
`weight_kg` is in kilograms.

### Temporal columns

| Type | Pattern | Example |
|---|---|---|
| Date (day) | `date_<event>` | `date_order`, `date_delivery`, `date_creation` |
| Timestamp | `ts_<event>` | `ts_creation`, `ts_update` |
| Year | `year` | — |
| Month | `month` | — (numeric 1-12) |
| Week | `week_iso` | — (ISO 8601) |

All dates are `DATE` (no timestamp if time is unnecessary). All timestamps are
UTC — local time conversion happens in the BI tool, not in the model.

### Boolean columns

Pattern: `is_<state>` — returns `TRUE` / `FALSE`.

| Example | Meaning |
|---|---|
| `is_active` | Is the customer active? |
| `is_delivered` | Is the order delivered? |
| `is_delayed` | Is the delivery delayed compared to the expected date? |

Never use `flag_`, or `0`/`1`. Booleans are booleans, not integers.

### Technical / metadata columns

Every Silver and Gold table carries technical columns for traceability:

| Column | Type | Description |
|---|---|---|
| `_source_system` | VARCHAR | Source system (`'sap'`, `'mes'`, `'plm'`) |
| `_loaded_at` | TIMESTAMP | Timestamp of loading into the layer |
| `_updated_at` | TIMESTAMP | Timestamp of last update |
| `entity` | VARCHAR | Group entity code (`'D'`, `'B'`, etc.) |

The `_` prefix signals a technical column (not business). BI tools can hide
them by default.

## Cloud storage naming (ADLS)

### Path structure

```
<container>/company_<entity>/<source>/<object>/YYYY/MM/DD/<object>.parquet
```

`<entity>` is the lowercase **data** entity code (`d`, `b`, ...) — the same
value stored in the `entity` column (see [Technical / metadata
columns](#technical-metadata-columns)), not the Azure infra `scope` code
(`dti`, `bg`) used in resource names. See the correspondence table in
[Azure landing zones](azure-landing-zones.md#resource-naming-pattern).

```
bronze/company_d/sap/order/2027/01/15/order.parquet
bronze/company_d/mes/production/2027/01/15/production.parquet
silver/company_d/stg_sap__order/
gold/company_d/dim_customer/
gold/company_d/fct_order/
gold/group/fct_order_group/
```

| Rule | Justification |
|---|---|
| All lowercase, snake_case | Consistency, Linux/Windows compatibility |
| No spaces, no special characters | Tool compatibility (DuckDB, Spark, Metabase) |
| Time partitioning in bronze only | Silver and Gold are managed by dbt/DuckDB, not by folder structure |
| Gold folder names = dbt model names | Single naming repository |

## Git naming

Branch and commit conventions are documented once, in
[Repositories and delivery](repositories-and-delivery.md#branching) — not
repeated here, so the two pages can't drift apart the way a copy-pasted rule
always eventually does.

## Allowed abbreviations

To avoid 40-character names, certain abbreviations are allowed — only these.
Any other abbreviation must be added to this list before use; if in doubt,
write the full word.

| Abbreviation | Meaning | Usage context |
|---|---|---|
| `excl_tax` | Excluding tax | Amount columns |
| `incl_tax` | Including tax | Amount columns |
| `tax` | VAT / Tax | Amount columns |
| `qty` | Quantity | Measure columns |
| `cnt` / `num` | Count / Number | Counting columns |
| `rev` | Revenue | Mart names, metrics |
| `ts` | Timestamp | Temporal columns |
| `sk` | Surrogate key | Technical keys |
| `id` | Identifier | Natural keys |
| `ref` | Reference | Product code, supplier code |
| `dt` | Date | Only in partition prefixes (`dt=2027-01-15`) |
| `min` | Minutes | Duration columns |
| `kg` | Kilograms | Weight columns |

## Anti-patterns — what we never do

| Anti-pattern | Why it's a problem | What to do instead |
|---|---|---|
| `data`, `data2`, `tmp_data` | Meaningless name | Name the business object |
| `tbl_orders`, `vw_customers` | Object type is already in the dbt prefix (`stg_`, `dim_`) | Remove technical SQL prefix |
| `customer_name`, `customer_firstname` in `dim_customer` | Table context is sufficient | `name`, `firstname` |
| `AMOUNT` (uppercase) | Inconsistent with snake_case | `amount_excl_tax` |
| `montant_commande` (non-English in a Gold table) | Inconsistent with the global English rule | `order_amount_excl_tax` |
| `date` column (unspecified) | Date of what? | `date_order`, `date_delivery` |
| `flag_active` returning `0`/`1` | Not a clean boolean | `is_active` returning `TRUE`/`FALSE` |
| Mixing camelCase and snake_case | Two conventions = confusion | snake_case only |
