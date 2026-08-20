# Testing

A model without a test is not finished. This page says which test to write,
where, and — more usefully — which ones not to write.

## What a dbt test actually is

A query that returns the rows that **should not exist**. Zero rows returned is a
pass. Nothing more sophisticated is going on, and knowing this is what makes a
failure easy to investigate: the compiled test SQL sits in
`target/compiled/.../` and can be run by hand to look at the offending rows.

```sql
-- the compiled form of a not_null test
select revenue
from "warehouse"."main"."mart_sales__daily_orders"
where revenue is null
```

## The four built-in tests

dbt Core ships **four** generic tests. Everything else comes from a package or
is written by hand.

| Test | Asserts | Where it belongs |
|---|---|---|
| `unique` | no duplicate values | the primary key of every model. The highest-value test there is |
| `not_null` | no NULLs | keys, and any column that is summed or divided by |
| `accepted_values` | only the listed values occur | status, type and reason codes |
| `relationships` | every value exists in the referenced table | every foreign key |

!!! warning "`unique` is for primary keys only"
    Before writing `unique`, ask whether the column *identifies a row of this
    table*. A foreign key is meant to repeat — `unique` on it asserts something
    false, and the test will be red forever.

## Tests from `dbt_utils`

`dbt_utils` is a dependency of every entity project. Its tests **must be
prefixed with the package name**, or dbt looks for a macro of that name in the
project, fails to find it, and stops at parse time.

| Test | Asserts |
|---|---|
| `unique_combination_of_columns` | uniqueness across several columns — the composite-key case |
| `expression_is_true` | any business rule expressible in SQL (`date_end >= date_start`) |
| `accepted_range` | numeric bounds, with `inclusive` (default `true`) |
| `relationships_where` | referential integrity with a filter, for documented exceptions |
| `not_accepted_values` | a blacklist of values |
| `not_null_proportion` | tolerates NULLs up to a threshold (`at_least: 0.95`) |
| `at_least_one` | the column is not entirely empty |
| `not_constant` | the column holds more than one distinct value |
| `not_empty_string` | catches `''`, which `not_null` lets through |
| `recency` | the newest row is less than N days old — detects a dead pipeline |
| `equal_rowcount`, `fewer_rows_than`, `equality` | comparisons between two models |
| `mutually_exclusive_ranges` | date ranges that must not overlap |
| `sequential_values` | no gap in a sequence |

### Required syntax

Arguments to a generic test are nested under `arguments:`. The flat form still
works and is deprecated — it emits
`MissingArgumentsPropertyInGenericTestDeprecation` and will eventually fail.

```yaml
- name: capacity_hours_per_day
  tests:
    - not_null
    - dbt_utils.accepted_range:
        arguments:
          min_value: 0
          max_value: 24
```

## The four kinds of test

| Kind | Where it lives | Use it for |
|---|---|---|
| **Generic** | YAML, under `tests:` | 90% of what you write. Parametrised and reusable |
| **Singular** | a `.sql` file in `tests/` | one rule too specific to parametrise |
| **Custom generic** | a macro `{% test my_test(model, column_name) %}` | the third time you write the same singular test |
| **Unit test** | YAML, with mocked inputs and expected outputs | testing **logic**, not data |

Unit tests are the only kind CI can run, because they need neither a warehouse
nor credentials: the inputs are fixtures written in the YAML. Use them for logic
whose failure case real data does not produce yet — the classic being a source
holding more than one daily partition.

## Where to test what

The principle: **test where the guarantee is created, not everywhere it is
relied upon.** Re-asserting a guarantee three layers down tests dbt, not the
data.

| Layer | What to test | What it catches |
|---|---|---|
| `stg_` | the **source contract**: natural key unique and not null, codes within their accepted values, mandatory fields present | the day the source system changes without telling you. This is the upstream alarm |
| `int_` | usually nothing — unless the grain changed, in which case test the new grain | a reshape that silently duplicated rows |
| `dim_` / `fct_` | the **grain** (unique on the key), foreign keys via `relationships`, measures within possible bounds | a join that multiplied a measure |
| `mart_` | the **business invariants**: a rate between 0 and 1, no future dates, no negative total | the figure that would be challenged in a meeting |

### The minimum bar

A model is not finished until it has, at least:

- `unique` **and** `not_null` on its key — or `unique_combination_of_columns`
  when the key is composite
- `relationships` on every foreign key
- `accepted_values` on every code column

Anything beyond that should be justified by a specific risk, not by a wish to
look thorough.

## Choosing a test

| The rule you want to state | The test |
|---|---|
| this column identifies a row | `unique` + `not_null` |
| these columns together identify a row | `dbt_utils.unique_combination_of_columns` |
| this value must exist elsewhere | `relationships` |
| ... except in a known, documented case | `dbt_utils.relationships_where` |
| this code comes from a fixed list | `accepted_values` |
| this number is physically impossible outside a range | `dbt_utils.accepted_range` |
| this must be strictly positive | `dbt_utils.accepted_range` with `min_value: 0, inclusive: false` |
| one column must be greater than another | `dbt_utils.expression_is_true` |
| the pipeline must have run recently | `dbt_utils.recency` |

!!! tip "Bounds beat blacklists"
    `not_accepted_values: [0]` forbids zero and allows −50. A lower bound states
    the actual rule and catches both.

## Severity and thresholds

```yaml
- unique:
    config:
      severity: warn        # or: error_if: ">10"
      store_failures: true
```

- **`severity: warn`** is legitimate, but only with the reason written next to
  it. A downgrade with no explanation is indistinguishable from giving up.
- **`error_if` / `warn_if`** express a tolerance — "fail only above ten
  offending rows" — which is honest for known dirty sources and dishonest as a
  way to keep a dashboard green.
- **`store_failures: true`** writes the offending rows to a table so they can be
  inspected in SQL rather than by re-running the test by hand. Worth enabling on
  any test that fails more than once.

## Anti-patterns

| Anti-pattern | Why it hurts |
|---|---|
| Re-testing the same guarantee at three layers | tests dbt, not the data, and triples the run time |
| A test that is permanently red | teaches everyone to ignore failures, and hides the next real one |
| `unique` on a foreign key | asserts something false about the model's grain |
| A blacklist where a bound is meant | catches the value you thought of, not the ones you did not |
| Adding tests to raise a count | 100 tests of which 60 are tautologies is worse than 40 that mean something |
| Testing what the warehouse already enforces | the column is typed `date`; it will not contain "hello" |

## Related

- [Data layers](data-layers.md) — what belongs in each layer
- [Naming conventions](naming-conventions.md) — the key and column patterns the
  tests above assert
- [Writing descriptions](writing-descriptions.md) — the other half of what makes
  a model finished
