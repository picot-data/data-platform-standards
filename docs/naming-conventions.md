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
| Metric (a column in a mart) | — | `<metric_name>` | `revenue` |

A **business entity** is a real-world object the business describes, not an
event it measures — `customer`, `product`, `date`, `supplier`, `plant`. A
**business process** is a measurable event involving one or more of those
entities — `order`, `delivery`, `production_run`. That distinction is what
separates `dim_` from `fct_` (see [Why a star
schema](data-layers.md#why-a-star-schema-not-marts-built-directly-from-staging)).

The double underscore `__` is a semantic separator: it separates the object's
origin (source) or the analysis domain. **Source names** reflect the
originating system, not the content — `stg_sap__order`, not `stg_sales__order`,
so that a future `stg_ebiz__order` from a different system stays
distinguishable. **Domain names** in marts reflect the business organization
(`finance`, `production`, `quality`, `sales`, `hr`). If a mart crosses multiple
domains, choose the primary one and document it in the dbt description.

Keep staging thin: no joins, no aggregation. A `stg_` model that needs a join
is an `int_` model.

Where each layer is materialized and what gets published to ADLS is a
different question, answered in
[Data layers — Persistence per layer](data-layers.md#persistence-per-layer).

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
| `entity` | VARCHAR | Group entity code — same code as the Azure infra `scope` (`'dti'` = Dirickx, `'bg'` = B&G, etc.) |

The `_` prefix signals a technical column (not business). BI tools can hide
them by default.

## Cloud storage naming (ADLS)

### Path structure

```
<container>/company_<entity>/<source>/<object>/YYYY/MM/DD/<object>.parquet
```

`<entity>` is the entity code — the same value stored in the `entity` column
(see [Technical / metadata columns](#technical-metadata-columns)) and the
same code used for the Azure infra `scope` segment in resource names (see
[Azure landing zones](azure-landing-zones.md#resource-naming-pattern)). One
code, no separate data/infra mapping to maintain.

```
bronze/company_dti/sap/order/2027/01/15/order.parquet
bronze/company_dti/mes/production/2027/01/15/production.parquet
silver/company_dti/stg_sap__order/
gold/company_dti/dim_customer/
gold/company_dti/fct_order/
gold/group/fct_order_group/
```

| Rule | Justification |
|---|---|
| All lowercase, snake_case | Consistency, Linux/Windows compatibility |
| No spaces, no special characters | Tool compatibility (DuckDB, Spark, Metabase) |
| Time partitioning in bronze only | Silver and Gold are managed by dbt/DuckDB, not by folder structure |
| Gold folder names = dbt model names | Single naming repository |

## BI naming

Metabase collections, user groups, serving databases and the dashboard
certification markers are documented once, in
[BI and access](bi-and-access.md) — not repeated here. Two rules from this page
apply to them unchanged: group names are `snake_case`, and the entity code in a
group or database name is the same code used for the Azure infra `scope`
segment and the `entity` column.

The one deliberate departure: dashboard and question *titles* in Metabase are
business-facing prose, so they are not bound by the `snake_case` and
no-special-characters rules above — they carry an emoji marker by design. dbt
model names never do.

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
