# Naming checklist (enforceable form)

Condensed from `docs/naming-conventions.md`, `docs/building-a-data-model/data-layers.md` and
`docs/building-a-data-model/project-structure.md`. The prose pages carry the reasoning; this file
carries only what can be checked mechanically.

## Universal

- `snake_case` everywhere. No camelCase, no kebab-case, no uppercase.
- English only. `chiffre_affaires`, `montant_commande` are violations.
- No accents, no special characters.
- Singular table names: `dim_customer`, never `dim_customers`.
- No redundant prefix repeating the table: in `dim_customer`, the column is
  `name`, not `customer_name`.
- Abbreviations only from the allowed list: `excl_tax`, `incl_tax`, `tax`,
  `qty`, `cnt`, `num`, `rev`, `ts`, `sk`, `id`, `ref`, `dt`, `min`, `kg`.
  Anything else is a violation until it is added to the list in
  `docs/naming-conventions.md`.

## Model names

| Layer | Pattern | Example |
|---|---|---|
| source declaration file | `_<source>__sources.yml` | `_sap__sources.yml` |
| staging | `stg_<source>__<object>` | `stg_sap__order` |
| intermediate | `int_<description>` | `int_order_enriched` |
| dimension | `dim_<business_entity>` | `dim_customer` |
| fact | `fct_<business_process>` | `fct_order` |
| mart | `mart_<domain>__<analysis>` | `mart_finance__monthly_revenue` |

- The source segment names the **system**, not the content:
  `stg_sap__order`, never `stg_sales__order`.
- Mart domains are business organisation names: `finance`, `production`,
  `quality`, `sales`, `hr`.
- `dim_` = a real-world object (customer, product, plant, date).
  `fct_` = a measurable event (order, delivery, production_run).
  A `dim_` holding measures, or a `fct_` copying dimension attributes instead
  of referencing them by key, is in the wrong layer.
- A `stg_` model that joins or aggregates is an `int_` model.
- Only `stg_` models may call `source()`.

## Column names

| Kind | Pattern | Example |
|---|---|---|
| natural primary key | `<object>_id` | `order_id` |
| surrogate key | `<object>_sk` | `order_sk` |
| foreign key | same name as the referenced PK | `customer_id` in `fct_order` |
| amount | `amount_<precision>` | `amount_excl_tax` |
| quantity | `qty_<object>` | `qty_ordered` |
| **rate / ratio** | `rate_<object>` | `rate_scrap`, `rate_margin` |
| weight | `weight_<unit>` | `weight_kg` |
| duration | `duration_<unit>` | `duration_min` |
| date (day) | `date_<event>` | `date_order` |
| timestamp (UTC) | `ts_<event>` | `ts_creation` |
| year / month / week | `year`, `month`, `week_iso` | — |
| boolean | `is_<state>` | `is_active` |

- `rate_` is reserved for **dimensionless ratios**. A price per hour is an
  amount, not a rate — `rate_cost_hour` for a currency-per-hour figure is a
  violation of the prefix and a trap for anyone who assumes 0–1 bounds.
- `_sk` means generated (`dbt_utils.generate_surrogate_key`); `_id` means it
  carries business meaning in the source system.
- Never `flag_`, never `0`/`1` for a boolean.
- A bare `date` column is a violation — date of what?
- The unit belongs in the name whenever it is not obvious.

## Technical columns

Every Silver and Gold table carries `_source_system`, `_loaded_at`,
`_updated_at` and `entity`. The `_` prefix marks a technical column; `entity`
has no underscore because it is part of the data model (`'dti'`, `'bg'`).

## File placement

- `_<source>__sources.yml` lives in `models/staging/<source>/`. dbt only reads
  YAML under `model-paths` — elsewhere it is silently ignored.
- Model properties: `_<source>__models.yml` in staging,
  `_<layer>__models.yml` elsewhere. Unit tests: `_<source>__unit_tests.yml`.
- Split `staging/` at the second **source system**; split `marts/` at the
  second **business domain**. Not before.
- Model names are globally unique in a project — folders create no namespace.

## Anti-patterns that are always a finding

| Seen | Say this |
|---|---|
| `data`, `tmp_data`, `data2` | meaningless name; name the business object |
| `tbl_orders`, `vw_customers` | the dbt prefix already carries the type |
| `customer_name` inside `dim_customer` | redundant with the table |
| `AMOUNT` | uppercase, breaks snake_case |
| `flag_active` returning 0/1 | `is_active` returning TRUE/FALSE |
| `date` with no event | `date_order`, `date_delivery` |
| non-English column in a Gold table | English only |
