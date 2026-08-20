---
name: reviewing-dbt-yaml-against-standards
description: >
  Reviews a dbt properties YAML file (_*__models.yml, _*__sources.yml) against the
  Picot group's data-platform standards and reports findings — it never edits the file.
  Use when asked to review, check, audit or "is this compliant" for a dbt schema/properties
  YAML, before opening a PR on an entity dbt project, or when a dbt parse error mentions a
  test that cannot be found. Catches unique on a foreign key, dbt_utils tests missing the
  package prefix, arguments not nested under arguments:, blacklists where a bound was meant,
  descriptions that restate the column name, and naming-convention violations.
metadata:
  author: picot-data
  standards: https://picot-data.github.io/data-platform-standards/
---

# Reviewing a dbt YAML against the Picot standards

**This skill reports. It does not edit.** Produce findings; let the human
decide. If the user then asks for the fixes to be applied, apply exactly the
findings you reported — do not silently widen the change, and do not write a
description (see the boundary at the end of this page).

Generic dbt correctness is not this skill's job — the dbt Labs skills cover
that. This skill checks the **delta**: the rules that are specific to this
group and that no generic reviewer knows about.

## Rules to load

Read these before reporting anything. They are the enforceable, condensed form
of the published standards:

- [Testing checklist](../../references/testing-checklist.md) — the four
  built-in tests, the `dbt_utils` catalogue, the two syntax rules, where to
  test what, the minimum bar
- [Naming checklist](../../references/naming-checklist.md) — model and column
  patterns, prefixes, allowed abbreviations, file placement
- [Description checklist](../../references/description-checklist.md) — the
  grain-first rule and what each layer's description must answer

The reasoning behind every rule is in the published site —
<https://picot-data.github.io/data-platform-standards/> (`testing`,
`naming-conventions`, `writing-descriptions`, `project-structure`,
`data-layers`). Quote the reason, not just the rule: a finding a reviewer
cannot justify gets argued away.

## Procedure

### 1. Establish the layer of every model in the file

Read the model prefix (`stg_`, `int_`, `dim_`, `fct_`, `mart_`). Almost every
rule is layer-dependent — the right test battery, the expected description
shape, and the folder the file should live in all follow from it. If a model's
prefix and its folder disagree, that is finding number one.

### 2. Read the model SQL where it exists

You cannot tell a primary key from a foreign key out of the YAML alone. Open
the `.sql` next to the YAML: the `GROUP BY`, the join keys, the
`generate_surrogate_key` call and the `select` list tell you the grain. Say so
explicitly in a finding if the SQL was unavailable and you inferred the grain
from names — an inferred grain is a weaker claim and the reader must know.

### 3. Walk the checks

**Test correctness**

- `unique` on a column that is not the model's primary key. The classic is a
  foreign key: it is *meant* to repeat, so the test asserts something false and
  goes red forever. Check every `unique` against the grain established in
  step 2.
- Missing minimum bar: `unique` + `not_null` on the key (or
  `dbt_utils.unique_combination_of_columns` when composite), `relationships`
  on every foreign key, `accepted_values` on every code column.
- A test in the `dbt_utils` catalogue written **without** the `dbt_utils.`
  prefix. This is not a style point — dbt looks for a project macro of that
  name, does not find it, and fails at parse time.
- Test arguments not nested under `arguments:`. The flat form still parses and
  emits `MissingArgumentsPropertyInGenericTestDeprecation`; it will eventually
  fail. `config:` stays a sibling of `arguments:`, never inside it.
- `not_accepted_values: [0]` (or any blacklist) where a bound was meant. It
  forbids zero and cheerfully allows −50. Recommend
  `dbt_utils.accepted_range` with `min_value: 0, inclusive: false`.
- The same guarantee re-asserted at a layer that did not create it, and
  tautological tests added to raise a count.
- `severity: warn` with no reason written beside it.

**Naming**

- Model name against its layer pattern; source segment naming the system
  (`stg_sap__order`) rather than the content (`stg_sales__order`).
- Column prefixes. The one most often got wrong: **`rate_` is reserved for
  dimensionless ratios.** A currency-per-hour figure is an amount, not a rate,
  and a reader who assumes 0–1 bounds on a `rate_` column will be wrong.
- `is_` for booleans, `date_<event>` / `ts_<event>` for temporals, `_sk` vs
  `_id`, no redundant table prefix on a column, abbreviations restricted to
  the allowed list, English, `snake_case`, singular table names.
- Presence of the technical columns `_source_system`, `_loaded_at`,
  `_updated_at`, `entity` on Silver and Gold models.

**Descriptions**

- Missing entirely — CI blocks on this, so it is always a blocking finding.
- Present but restating the name ("the plant key of the work center"). It
  passes the CI gate and teaches nothing, which is the failure mode the gate
  itself created. Report it as a finding of equal weight to a missing one.
- Model description not leading with the grain ("One row per …").
- A `mart_` description that is not a business definition a controller could
  quote.
- A unit-bearing column with no unit, currency or timezone stated.
- Not in English.

**Placement** (only when you can see the tree)

- `_<source>__sources.yml` outside `models/staging/` — dbt silently ignores
  YAML outside `model-paths`, so the source declaration simply does not exist.
- A `source()` call outside a `stg_` model.
- File naming: `_<source>__models.yml` in staging, `_<layer>__models.yml`
  elsewhere.

### 4. Report

Group findings by severity and give each one a location, the rule, and the
fix. Keep the fix as a suggestion in the report — do not apply it yet.

| Severity | Means |
|---|---|
| **Blocking** | fails parse, fails CI, or asserts something false — missing description, missing `dbt_utils.` prefix, `unique` on a foreign key |
| **Should fix** | below the minimum bar, deprecated syntax, naming violation |
| **Consider** | a judgement call — a test that may be tautological, a description that could name the trap |

For each finding:

```
[Blocking] models/staging/sap/_sap__models.yml:42 — stg_sap__order.customer_id
  Rule: `unique` belongs on the primary key only (testing.md).
  Why:  customer_id is a foreign key here; the grain is one row per order, so
        the value repeats and this test is red by construction.
  Fix:  remove `unique`; keep `not_null` and add
        `relationships: to: ref('dim_customer'), field: customer_id`.
```

End with one line stating whether the file meets the minimum bar, and list
what is missing if it does not. If the file is clean, say so plainly — do not
manufacture a finding to look useful.

## The boundary you must not cross

If a description is missing or empty, **report it as a finding and stop
there.** Do not draft a replacement in the review, even a "suggested" one, and
even if the user asks in the same breath. A business definition is supplied by
a human and is never inferred from the data, the column name, or the SQL. A
fabricated definition is undetectable once written — it reads exactly like a
real one.

Drafting descriptions is a separate, deliberately constrained job: use the
`drafting-dbt-descriptions` skill, which knows which parts it is allowed to
write and which it must ask for.
