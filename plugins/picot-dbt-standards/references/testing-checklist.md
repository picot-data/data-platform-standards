# Testing checklist (enforceable form)

Condensed from `docs/building-a-data-model/testing.md`. The prose page carries the reasoning.

## The four built-in tests — and nothing else is built in

| Test | Asserts | Belongs on |
|---|---|---|
| `unique` | no duplicates | the **primary key only** |
| `not_null` | no NULLs | keys, and any column summed or divided by |
| `accepted_values` | only the listed values occur | status / type / reason codes |
| `relationships` | the value exists in the referenced table | every foreign key |

Everything else comes from `dbt_utils` and **must carry the package prefix**.
Without it dbt looks for a project macro of that name, fails to find it, and
stops at parse time.

## Syntax rules — both are hard requirements

**1. Package prefix.** `accepted_range` is wrong; `dbt_utils.accepted_range`
is right. Same for every test in the table below.

**2. Arguments nest under `arguments:`.** The flat form still parses but is
deprecated (`MissingArgumentsPropertyInGenericTestDeprecation`) and will fail.

```yaml
- name: capacity_hours_per_day
  description: >
    Machine availability in hours per calendar day, not opening hours.
  tests:
    - not_null
    - dbt_utils.accepted_range:
        arguments:
          min_value: 0
          max_value: 24
```

`config:` (severity, `store_failures`) stays a sibling of `arguments:`, not
inside it.

## The `dbt_utils` catalogue

| Test | Asserts |
|---|---|
| `unique_combination_of_columns` | uniqueness across several columns (composite key) |
| `expression_is_true` | any SQL-expressible rule (`date_end >= date_start`) |
| `accepted_range` | numeric bounds, `inclusive` defaults to `true` |
| `relationships_where` | referential integrity with a documented exception |
| `not_accepted_values` | a blacklist of values |
| `not_null_proportion` | tolerates NULLs up to `at_least:` |
| `at_least_one` | the column is not entirely empty |
| `not_constant` | more than one distinct value |
| `not_empty_string` | catches `''`, which `not_null` lets through |
| `recency` | newest row younger than N days — detects a dead pipeline |
| `equal_rowcount`, `fewer_rows_than`, `equality` | model-to-model comparison |
| `mutually_exclusive_ranges` | date ranges that must not overlap |
| `sequential_values` | no gap in a sequence |

## Where to test what

**Test where the guarantee is created, not everywhere it is relied upon.**
Re-asserting the same guarantee three layers down tests dbt, not the data.

| Layer | What to test |
|---|---|
| `stg_` | the **source contract**: natural key unique + not_null, codes within accepted values, mandatory fields present |
| `int_` | usually nothing — unless the grain changed, then test the new grain |
| `dim_` / `fct_` | the **grain** (unique on the key), `relationships` on every FK, measures within possible bounds |
| `mart_` | the **business invariants**: a rate between 0 and 1, no future date, no negative total |

## The minimum bar

A model is not finished until it has, at least:

- `unique` **and** `not_null` on its key — or
  `dbt_utils.unique_combination_of_columns` when the key is composite
- `relationships` on every foreign key
- `accepted_values` on every code column

Anything beyond that must be justified by a **named risk**, not by a wish to
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
| one column must exceed another | `dbt_utils.expression_is_true` |
| the pipeline must have run recently | `dbt_utils.recency` |

**Bounds beat blacklists.** `not_accepted_values: [0]` forbids zero and allows
−50. A lower bound states the actual rule and catches both.

## Severity

`severity: warn` is legitimate **only with the reason written next to it**; an
unexplained downgrade is indistinguishable from giving up. `error_if` /
`warn_if` express a tolerance — honest for a known dirty source, dishonest as a
way to keep a dashboard green. `store_failures: true` is worth enabling on any
test that has failed more than once.

## Anti-patterns — always a finding

| Anti-pattern | Why |
|---|---|
| `unique` on a foreign key | asserts something false about the grain; red forever |
| a `dbt_utils` test without the package prefix | parse-time failure |
| test arguments not nested under `arguments:` | deprecated, will fail |
| a blacklist where a bound is meant | catches the value you thought of, not the ones you did not |
| re-testing the same guarantee at three layers | tests dbt, not the data |
| a permanently red test | teaches everyone to ignore failures |
| adding tests to raise a count | 100 tests of which 60 are tautologies is worse than 40 that mean something |
| testing what the warehouse enforces | a `date` column will not contain "hello" |
