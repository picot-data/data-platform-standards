---
name: generating-dbt-test-battery
description: >
  Generates the dbt test battery a model needs to meet the Picot group's minimum bar —
  unique + not_null on the key, relationships on every foreign key, accepted_values on every
  code column, bounds on physical measures — in the group's required YAML syntax
  (dbt_utils. prefix, arguments nested under arguments:). Use when adding tests to a new or
  untested dbt model, when asked "what tests does this model need", or when finishing a model
  before a PR. Applies the "test where the guarantee is created" rule so it does not pile
  tautological tests onto downstream layers.
metadata:
  author: picot-data
  standards: https://picot-data.github.io/data-platform-standards/
---

# Generating a dbt test battery

A model without a test is not finished. This skill derives the battery
mechanically from the model's grain and column roles, in this group's syntax.

It does **not** decide business rules. A business invariant on a `mart_` — what
counts as a sale, which statuses are excluded — comes from a human, the same
way a definition does. Generate the structure, and ask for the rule.

## Rules to load

- [Testing checklist](../../references/testing-checklist.md) — the four
  built-in tests, the `dbt_utils` catalogue, the two syntax rules, the layer
  table, the minimum bar, the anti-patterns
- [Naming checklist](../../references/naming-checklist.md) — needed to read
  column roles off their names (`_id`, `_sk`, `rate_`, `qty_`, `amount_`,
  `is_`, `date_`)

Reasoning: <https://picot-data.github.io/data-platform-standards/testing/>.

## Procedure

### 1. Read the SQL, not just the YAML

The grain is the whole input to this skill and it cannot be guessed from
column names. Establish from the `.sql`:

- the **primary key** — the `generate_surrogate_key` call, the `GROUP BY`, or
  the declared natural key. Composite or single?
- the **foreign keys** — columns joined to a dimension, or `_id` / `_sk`
  columns that are not the PK
- the **code columns** — anything compared against a fixed set, or a
  `status` / `type` / `reason` column
- the **physical measures** — quantities, weights, durations, amounts, rates

If the SQL is not available, say so and state the grain you assumed. Do not
emit a battery built on a silently guessed grain.

### 2. Check the layer before generating anything

**Test where the guarantee is created, not everywhere it is relied upon.**

| Layer | Generate |
|---|---|
| `stg_` | the source contract: natural key `unique` + `not_null`, `accepted_values` on codes, `not_null` on mandatory fields |
| `int_` | **usually nothing.** Only if the grain changed — then the new grain |
| `dim_` / `fct_` | the grain, `relationships` on every FK, bounds on measures |
| `mart_` | business invariants only — and those come from the user (step 4) |

If you are about to re-assert on `fct_order` a guarantee already tested on
`stg_sap__order`, stop: that tests dbt, not the data, and triples the run
time. Say which upstream model already covers it.

### 3. Derive the battery

| Column role | Test |
|---|---|
| single primary key | `unique` + `not_null` |
| composite primary key | `dbt_utils.unique_combination_of_columns` on the model, plus `not_null` on each part |
| foreign key | `relationships` to the referenced dimension, plus `not_null` if mandatory |
| code column | `accepted_values` with the values listed |
| quantity / weight / duration | `dbt_utils.accepted_range` with the physical floor (usually `min_value: 0`) |
| strictly positive measure | `dbt_utils.accepted_range` with `min_value: 0, inclusive: false` |
| `rate_` (dimensionless ratio) | `dbt_utils.accepted_range` with `min_value: 0, max_value: 1` — but confirm the ratio is not expressed in percent |
| paired dates | `dbt_utils.expression_is_true` (`date_end >= date_start`) |
| a table that must be refreshed | `dbt_utils.recency` on the model |

**Bounds beat blacklists.** Never emit `not_accepted_values: [0]` when the rule
is "must be positive" — it forbids zero and allows −50.

**Do not pile on.** Do not emit `not_constant`, `at_least_one`,
`not_empty_string` or `recency` unless a **named risk** justifies each one.
100 tests of which 60 are tautologies is worse than 40 that mean something.
Do not test what the warehouse already enforces: a `DATE` column will not
contain "hello".

### 4. Ask for what you cannot derive

Stop and ask, rather than guessing, when:

- an `accepted_values` list must be enumerated and you have not seen the data
  or a source declaration listing the codes. Do not invent plausible statuses.
  Either ask, or propose running `dbt show` and offer the observed values as a
  candidate list the user must confirm is *complete* — observed values are not
  the accepted set.
- a measure's plausible bound is a business fact rather than a physical one
  ("can a discount be negative?").
- a `mart_` invariant is required — that is a business rule, and it is the
  user's to state.
- a foreign key's referenced model does not exist yet.

List the open questions explicitly instead of emitting a battery that looks
complete and is not.

### 5. Emit the YAML in the required syntax

Two rules, both hard:

1. **`dbt_utils.` prefix on every package test.** Without it dbt looks for a
   project macro of that name and fails at parse time.
2. **Arguments nest under `arguments:`.** The flat form is deprecated and will
   fail. `config:` is a sibling of `arguments:`, not a child.

```yaml
models:
  - name: fct_production_operation
    description: >
      One row per production order and routing step.
    columns:
      - name: production_operation_sk
        description: >
          Surrogate key over (production_order_id, operation_number).
        tests:
          - unique
          - not_null

      - name: work_center_id
        description: >
          Work centre the operation ran on.
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_work_center')
                field: work_center_id

      - name: operation_status_code
        tests:
          - accepted_values:
              arguments:
                values: ['REL', 'CNF', 'TEC', 'DLV']

      - name: duration_min
        tests:
          - not_null
          - dbt_utils.accepted_range:
              arguments:
                min_value: 0
              config:
                severity: warn   # source known to emit zero-length setups
```

Composite key, tested on the model rather than a column:

```yaml
    tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - production_order_id
              - operation_number
```

### 6. Report what you generated and what you did not

State the minimum bar explicitly: key covered, every FK covered, every code
column covered — or which one is not, and why (usually: waiting on an answer
from step 4). A battery that silently skips a foreign key looks finished and
is not.

## Descriptions are not this skill's job

The YAML you emit will sit next to `description:` fields. Fill in only the
mechanical ones you can genuinely derive; leave a business definition to the
user. Use `drafting-dbt-descriptions` for that — it is the skill that knows
where the line is. Never invent a definition to make the emitted YAML pass CI.
