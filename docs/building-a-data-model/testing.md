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

!!! warning "`expression_is_true` compiles to `select 1`"
    Run its compiled file by hand and you get a count, not the rows. It selects
    the offending rows only when `store_failures` is on — which is another reason
    that setting is not optional. Read the audit table, not the compiled SQL.

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

## Name every test whose generated name is unreadable

Left unnamed, dbt builds the test name from the test type plus every argument:

```
dbt_utils_expression_is_true_stg_sap__production_order_date_actual_end_date_actual_start
```

That string is not an internal detail. It is what appears in the alert sent when
the test fails, in the Dagster asset check, and as the **table name** under
`_dbt_test__audit` that the offending rows are written to. A reader then has to
decode an expression instead of reading a claim, and querying the audit table
means finding a truncated hash first.

```yaml
- dbt_utils.expression_is_true:
    name: production_order_actual_dates_run_forwards
    arguments:
      expression: date_actual_end >= date_actual_start
```

`name:` is a sibling of `arguments:` and `config:`, not a child. The convention
is **`<model scope>_<what must be true>`** — the prefix is not decoration, dbt
requires test names to be unique across the whole project.

Which tests need it: every `dbt_utils.expression_is_true` and
`dbt_utils.accepted_range`, and `relationships`. Which do not: `not_null`,
`unique` and `accepted_values`, whose generated names already read as the rule
they enforce — `accepted_values_..._plant_id__P100__P200` even lists the values.
The criterion is not length, it is whether the name states what must be true.

## Severity: three tiers, and the choice is a decision

A failing test at `error` fails the whole `dbt build`, and therefore blocks
publication (see [Data layers](data-layers.md)). That is the right default and it
has a consequence worth stating plainly: **leaving every test at `error` means
one absurd date in one row can hold all of Gold hostage until somebody edits a
record in the source system.** That hands the refresh SLA to another team's
ticket queue.

So severity is assigned per test, on purpose, in one of three tiers.

| Tier | Meaning | Effect |
|---|---|---|
| `error` | nothing publishable can be computed until this is fixed | blocks. Reserved for the key, and for anything that makes "one row" meaningless |
| `warn` | anomalous, but it invalidates no total | publishes, records the rows, does not block |
| **quarantine** | a source error known to recur | handled *in the model*, not by a test |

```yaml
- dbt_utils.expression_is_true:
    name: production_order_planned_dates_run_forwards
    arguments:
      expression: date_planned_end >= date_planned_start
    config:
      # warn: a planned date the wrong way round distorts a lead-time figure
      # and nothing else. The day a mart_ computes a planned lead time, this
      # test is that model's dependency and belongs back at error.
      severity: warn
```

Rules that make the tiers hold:

- **A downgrade carries its reason, next to it, in the YAML.** A `warn` with no
  explanation is indistinguishable from giving up, and it is the normal way a
  build gets unblocked at 18:00 on a Friday.
- **Write the condition that would move it back.** The comment above is useful
  because it names what has to change. "warn for now" does not.
- **`error_if` / `warn_if`** express a tolerance — "fail only above ten offending
  rows" — honest for a known dirty source, dishonest as a way to keep a dashboard
  green.

### Never `warn` a foreign key

The tempting third option for an orphan foreign key is `severity: warn`. It is
the worst of the three: the orphan is published, then vanishes from every inner
join downstream, so the per-product total comes out too low with nothing to show
for it. The anomaly is both live and invisible.

The answer is quarantine. Either an `UNKNOWN` member in the dimension that
orphans attach to — the group total stays right and the anomaly becomes readable
in the dashboard as "600 units on unknown product" — or an explicit exclusion
**with the excluded rows counted** in a rejects model. The distinction that
matters:

!!! danger "Filtering is not quarantining"
    Silently dropping a bad row turns a visible error into an invisible one. The
    pipeline is green, the dashboard is green, the number is wrong. Rows may be
    set aside; they may never be set aside uncounted.

## `store_failures` is on for the whole project

Not per test, and not passed on the command line:

```yaml
# dbt_project.yml
data_tests:
  +store_failures: true
```

A test fails at 03:00 in a scheduled run nobody is watching. The default keeps
the count and throws the rows away, so the first question the next morning —
*which rows?* — requires re-running the build, by which time the source may have
moved and the evidence is gone.

Cost: one table per test under `<schema>_dbt_test__audit`, most of them empty.
That schema belongs to no model folder, so publication never sees it and nothing
leaks into the serving databases the BI tool reads. The tables are recreated on
every run — this is evidence for the run that just failed, not a history.

Side benefit: dbt then prints the exact query to run in its own error output, so
investigating stops being a treasure hunt.

## When a test goes red

1. **Read which test.** The alert or the Dagster asset check names it. With
   readable test names, this is often the whole investigation.
2. **Read the rows** in `<schema>_dbt_test__audit`.
3. **Qualify it.** Source error, or too-strict test? This is the only question
   that matters, and it decides everything after.
    - Source error → a ticket to the source owner. The pipeline stays red, which
      is it doing its job.
    - Too-strict test → a plant opened and nobody said so. Fix the test, commit,
      CI validates, re-run.
4. **Communicate freshness.** The most commonly skipped step. Consumers must be
   able to see "data as of the 20th" without asking anyone.
5. **Re-run.** The pipeline is idempotent; there is no manual data repair.

!!! note "Do not optimise the re-ingestion, reduce what blocks"
    A fix in the source system takes hours to days. Re-extraction takes minutes
    to hours. The bottleneck is never the pipeline, so making it faster changes
    nothing — and a daily schedule picks the correction up on its own. "This
    blockage is unbearable" is the symptom of a test sitting at `error` that
    belongs at `warn` or in quarantine.

### Warnings need their own alert

A `warn` does not fail the step, so the run succeeds and any failure hook stays
silent. Watching only failures therefore makes `warn` a way of making a problem
disappear rather than a decision to publish despite it — and a warning nobody
reads is the same as no test.

Warned data **has been published**. That is a different message from a blocked
pipeline and must not be worded like one: the reader is not being asked to
unblock anything, they are being told that a number they can already see was
computed over rows with a known anomaly.

## Anti-patterns

| Anti-pattern | Why it hurts |
|---|---|
| Re-testing the same guarantee at three layers | tests dbt, not the data, and triples the run time |
| A test that is permanently red | teaches everyone to ignore failures, and hides the next real one |
| `unique` on a foreign key | asserts something false about the model's grain |
| A blacklist where a bound is meant | catches the value you thought of, not the ones you did not |
| Adding tests to raise a count | 100 tests of which 60 are tautologies is worse than 40 that mean something |
| Testing what the warehouse already enforces | the column is typed `date`; it will not contain "hello" |
| Leaving every test at `error` | one bad row blocks every domain; the refresh SLA becomes another team's ticket queue |
| `severity: warn` on a foreign key | publishes the orphan *and* hides it in the joins — worse than either blocking or quarantining |
| Filtering bad rows without counting them | turns a visible error into an invisible one, which is the only failure nobody detects |
| Watching failures but not warnings | makes `warn` a way to hide a problem rather than a decision to publish despite it |
| Leaving a `dbt_utils` test unnamed | the generated name is what lands in the alert and names the audit table |

## Related

- [Data layers](data-layers.md) — what belongs in each layer
- [Naming conventions](../naming-conventions.md) — the key and column patterns the
  tests above assert
- [Writing descriptions](writing-descriptions.md) — the other half of what makes
  a model finished
