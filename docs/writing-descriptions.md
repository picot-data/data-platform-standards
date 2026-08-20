# Writing descriptions

Descriptions are not comments. Since [ADR 0021](adr-index.md) replaced DataHub
with `dbt docs`, **they are the catalogue** — the only place a reader learns what
a table holds and what a number means. CI fails on a missing one.

That gate creates a specific risk, and this page exists because of it: a
description that restates the column name passes the gate and teaches nothing.
A catalogue full of those is worse than no catalogue, because it looks complete.

## The one test that matters

> Would someone who has never opened the source system know, after reading this,
> **what the table contains** and **what one row represents**?

If the answer is no, the description is not written yet, whatever its length.

## Two rules that apply everywhere

**Lead with the grain.** "One row per …" is what a reader looks for first and
the fact that prevents the most expensive mistakes downstream. It belongs in the
first sentence of every model description.

**Never paraphrase the name.** `production_operation` described as "the
production operations" adds nothing. Say what an operation *is*, at what grain,
and what it is not.

## What each layer's description answers

| Layer | The question the description answers |
|---|---|
| **source** | what the source system sends, at what grain **in its own vocabulary**, snapshot or delta, and any known quirk of the export |
| **`stg_`** | one line: the grain, and what changed. Nothing more — staging is a thin pass-through, and the substance belongs in the columns |
| **`int_`** | **why this model exists.** It is scaffolding and has to justify itself. Plus its grain, which has usually changed |
| **`dim_`** | which business entity, its key, and how it behaves over time |
| **`fct_`** | the business process recorded, the grain **in the first line**, and the additivity of each measure |
| **`mart_`** | the **business definition** — the glossary entry, written for a controller and not for an engineer. What is included, what is excluded, and the decision behind every ambiguity |
| **column** | the unit, the currency, the timezone; whether the value is an observation or an assumption; and if it is a code, what the codes mean |

### Staging descriptions are supposed to be short

A staging model joins nothing and aggregates nothing, so its grain is the
source's grain and there is genuinely little to add. One line is correct:

```yaml
- name: stg_sap__work_center
  description: One row per SAP work center (mock seed until the real SAP extraction lands).
```

The effort goes into the **columns**, where there is no overlap with the source
declaration at all — sources are documented at table level, not column level. A
column description is where a reader learns that `capacity_hours_per_day` is
machine availability rather than opening hours.

### Mart descriptions are the glossary

The business definition of a term lives in the `description` of the `mart_`
model that computes it, and nowhere else — not in a separate glossary file that
would drift from the SQL. Write it for the person who will quote the number in a
meeting.

## Say the thing that cannot be guessed

The value of a description is concentrated in whatever the column name does not
already say. In order of usefulness:

1. **The trap.** An ambiguity, a value that means something unexpected, a grain
   that is not the obvious one. If a downstream reader could produce a wrong
   number in good faith, say so here.
2. **The unit.** Currency, hours, kilograms, timezone, tax included or excluded.
3. **Observation or assumption.** A standard cost rate and an invoiced amount
   look identical in a table and cannot be used for the same purposes.
4. **Provisional status.** If a definition is a placeholder awaiting a business
   owner, write that, and name who has to confirm it. An honest "to be confirmed
   with X" is worth more than a confident guess.

## Where the definition comes from

**A business definition is supplied by a human. It is never inferred from the
data, the column name, or the SQL.**

This applies to people and to any assistant or generator used to draft
documentation. A tool may:

- produce the **structure** — the grain sentence, the unit, the currency
- state the **mechanical facts** it can genuinely derive — "renamed from
  `cost_rate_hour`", "one row per order and routing step"
- and **mark explicitly as unresolved** anything requiring a business decision

A tool must **not** invent what a term means, which cases are included or
excluded, or how an ambiguity was resolved. When the definition is missing, the
correct behaviour is to **ask for it and stop** — not to fill the gap with a
plausible sentence. A fabricated definition is undetectable once written: it
reads exactly like a real one.

## Language and form

- **English**, like everything else in the repositories, including when the
  conversation that produced it happened in French. The catalogue is read across
  entities, and two of the three are not French-speaking.
- Full sentences, ending with a full stop.
- Use a YAML block scalar (`>`) as soon as the text exceeds one line.
- Naming a source-system term is helpful — "Plant (SAP `Werk`)" — as long as the
  meaning follows.

## Examples

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
    rows, since several work centres share a plant.

    It can differ from the plant of an order routed through it: a shared press
    or a centralised packing line serves orders launched elsewhere. So "output
    per plant" has two answers — the plant owning the order, and the plant where
    the work happened — both correct and different. Any model built on one of
    them has to say which.
```

The second one costs three minutes and prevents the meeting where two people
bring two different production figures.

## Related

- [Testing](testing.md) — the other half of what makes a model finished
- [Data layers](data-layers.md) — what belongs in each layer
- [Glossary](glossary.md) — group-wide business terms
