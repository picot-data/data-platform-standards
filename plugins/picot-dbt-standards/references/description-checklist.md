# Description checklist (enforceable form)

Condensed from `docs/building-a-data-model/writing-descriptions.md`. The prose page carries the
reasoning and the worked examples.

Since ADR 0021 replaced DataHub with `dbt docs`, **descriptions are the
catalogue**. CI fails on a missing one — which creates the specific risk this
page exists for: a description that restates the column name passes the gate
and teaches nothing. A catalogue full of those is worse than none, because it
looks complete.

## The one test

> Would someone who has never opened the source system know, after reading
> this, **what the table contains** and **what one row represents**?

If no, it is not written yet, whatever its length.

## Two rules that apply everywhere

1. **Lead with the grain.** "One row per …" belongs in the first sentence of
   every model description.
2. **Never paraphrase the name.** `production_operation` described as "the
   production operations" adds nothing.

## What each layer's description answers

| Layer | The question |
|---|---|
| source | what the system sends, at what grain **in its own vocabulary**, snapshot or delta, and any known quirk of the export |
| `stg_` | one line: the grain, and what changed. The substance goes in the columns |
| `int_` | **why this model exists** — it is scaffolding and must justify itself — plus its grain, which has usually changed |
| `dim_` | which business entity, its key, and how it behaves over time |
| `fct_` | the business process recorded, the grain **in the first line**, and the additivity of each measure |
| `mart_` | the **business definition** — the glossary entry, written for a controller: what is included, what is excluded, and the decision behind every ambiguity |
| column | the unit, the currency, the timezone; observation or assumption; and if it is a code, what the codes mean |

Staging descriptions being short is correct, not lazy. Sources are documented
at table level, not column level, so a `stg_` model's **columns** are where the
whole value sits — there is no overlap with the source declaration at all.

The business definition of a term lives in the `description` of the `mart_`
model that computes it, and nowhere else — not in a separate glossary file that
would drift from the SQL.

## Say the thing that cannot be guessed

In order of usefulness:

1. **The trap.** An ambiguity, a value that means something unexpected, a grain
   that is not the obvious one. If a downstream reader could produce a wrong
   number in good faith, say so.
2. **The unit.** Currency, hours, kilograms, timezone, tax included or excluded.
3. **Observation or assumption.** A standard cost rate and an invoiced amount
   look identical in a table and cannot be used for the same purposes.
4. **Provisional status.** If a definition is a placeholder awaiting a business
   owner, write that, and name who has to confirm it.

## Length, homes, and register

**Budget: 4 lines for a column, 12 for a model.** Not a target — a ceiling.
Past it, the text is a document and belongs in an ADR.

**One fact, one home:**

| Home | What belongs there |
|---|---|
| `description:` | grain, unit, meaning, trap. **All business scope, and nowhere else** |
| `.sql` comment | only what someone editing the query cannot read off the code — why a cast is `try_`, why a lookup is hand-transcribed. ≤ 2 lines. `dbt docs` shows the compiled SQL, so a business explanation here is a duplicate |
| ADR | a dated decision with an owner. The description carries the conclusion and the ADR number, not the reasoning |

**The volatility test — apply to every sentence:** *will this be false after the
next extract?* Row counts, distinct counts, totals and date ranges fail it and
come out. Exception: a figure that **changed a decision** stays, because
without it the decision reads as arbitrary.

**Register:**

- no capitals for emphasis — `dbt docs` renders them as shouting
- no closing sentence drawing out the consequence of the previous one
- no aphorism, no "and this is the trap of the model", no rhetorical
  construction of any kind
- the reader is a controller looking up a number, not an audience

## Where the definition comes from — the hard rule

**A business definition is supplied by a human. It is never inferred from the
data, the column name, or the SQL.**

This binds any assistant or generator. A tool **may**:

- produce the **structure** — the grain sentence, the unit, the currency
- state the **mechanical facts** it can genuinely derive — "renamed from
  `cost_rate_hour`", "one row per order and routing step"
- **mark explicitly as unresolved** anything requiring a business decision

A tool **must not** invent what a term means, which cases are included or
excluded, or how an ambiguity was resolved. When the definition is missing, the
correct behaviour is to **ask for it and stop** — not to fill the gap with a
plausible sentence. A fabricated definition is undetectable once written: it
reads exactly like a real one.

## Derivable vs. not derivable

| Derivable — write it | Not derivable — ask |
|---|---|
| the grain, read off the `GROUP BY` / join keys / declared PK | what the business means by the term the model computes |
| "renamed from `<source column>`", read off the SQL | whether a code value should be included or excluded |
| the unit **when the column name or the source declares it** (`weight_kg`, `duration_min`) | the currency, when no column or doc states it |
| the data type and nullability | whether a figure is an observation or an assumption |
| "one row per X and Y", from a composite key | why an ambiguity was resolved one way |
| the enumeration of code values present, as a list | what each code *means* |

## Language and form

- **English**, always, including when the conversation happened in French. The
  catalogue is read across entities and two of the three are not
  French-speaking.
- Full sentences, ending with a full stop.
- YAML block scalar (`>`) as soon as the text exceeds one line.
- Naming a source-system term is helpful — "Plant (SAP `Werk`)" — as long as
  the meaning follows.

## The two shapes of a finding

**Not written yet:**

```yaml
- name: plant_id
  description: The plant key of the work center.
```

Restates the column name. Passes CI. Teaches nothing.

**Written:**

```yaml
- name: plant_id
  description: >
    Plant (SAP `Werk`) the work centre physically stands in. Repeats across
    rows, since several work centres share a plant. It can differ from the
    plant of an order routed through it, so "output per plant" has two
    answers — owning plant and performing plant — and a model using one must
    say which.
```

Four lines, and every one of them carries a fact the name does not. The trap is
stated once and its consequence is the same sentence, not a paragraph.
