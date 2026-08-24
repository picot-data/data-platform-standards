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

## Name the tests whose generated name is unreadable

Unnamed, dbt builds the name from the test type plus every argument:
`dbt_utils_expression_is_true_stg_sap__production_order_date_actual_end_date_actual_start`.
That string is what lands in the failure alert, in the Dagster asset check, and
as the **audit table name** the offending rows are written to.

```yaml
- dbt_utils.expression_is_true:
    name: production_order_actual_dates_run_forwards
    arguments:
      expression: date_actual_end >= date_actual_start
```

`name:` is a sibling of `arguments:` and `config:`. Convention:
**`<model scope>_<what must be true>`** — the prefix is required, dbt enforces
project-wide uniqueness of test names.

| Needs a `name:` | Does not |
|---|---|
| `dbt_utils.expression_is_true`, `dbt_utils.accepted_range`, `relationships` | `not_null`, `unique`, `accepted_values` |

The criterion is not length: `accepted_values_..._plant_id__P100__P200` is long
and already states the rule, values included.

## Severity — three tiers, assigned per test

A test at `error` fails the whole `dbt build` and therefore blocks publication.
Leaving everything at `error` means one absurd row holds every domain hostage
until someone edits a record in the source system.

| Tier | Effect | Reserved for |
|---|---|---|
| `error` | blocks publication | the key, and anything making "one row" meaningless |
| `warn` | publishes, records the rows, does not block | anomalies that invalidate no total |
| **quarantine** | handled in the model, not by a test | source errors known to recur |

- A downgrade to `warn` carries **its reason and the condition that would move it
  back**, in a comment next to it. "warn for now" is not that.
- `error_if` / `warn_if` express a tolerance — honest for a known dirty source,
  dishonest as a way to keep a dashboard green.
- **Never `warn` a foreign key.** It publishes the orphan *and* loses it in every
  inner join, so the total is wrong with nothing to show for it — worse than
  blocking and worse than quarantining. Quarantine means an `UNKNOWN` dimension
  member, or an explicit exclusion **with the excluded rows counted**. Filtering
  without counting turns a visible error into an invisible one.

## `store_failures` is project-wide, not per test

```yaml
# dbt_project.yml
data_tests:
  +store_failures: true
```

A test fails at 03:00 in a run nobody watches; the default keeps the count and
discards the rows, so answering *which rows?* needs a rebuild. Do not propose
`--store-failures` as a flag or `store_failures: true` on one test — the project
setting is the standard. `dbt_utils.expression_is_true` also compiles to
`select 1` without it, so its compiled SQL shows a count and never the rows.

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
| every test left at the default `error` | one bad row blocks every domain; the SLA becomes another team's ticket queue |
| `severity: warn` on a foreign key | publishes the orphan *and* hides it in the joins |
| filtering bad rows without counting them | the only failure mode nobody ever detects |
| a `dbt_utils` test left unnamed | its generated name is what the alert and the audit table carry |
