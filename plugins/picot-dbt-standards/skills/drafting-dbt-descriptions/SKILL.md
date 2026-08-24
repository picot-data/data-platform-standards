---
name: drafting-dbt-descriptions
description: >
  Drafts dbt model and column descriptions to the Picot group's catalogue standard —
  grain-first, English, unit and currency stated — and refuses to invent any business
  definition, asking the user for it and stopping instead. Use when writing or improving
  descriptions in a dbt properties YAML, when CI fails on a missing description, or when a
  description restates the column name. The catalogue is dbt docs (ADR 0021), so these
  descriptions are the only documentation that exists.
user-invocable: false
metadata:
  author: picot-data
  standards: https://picot-data.github.io/data-platform-standards/writing-descriptions/
---

# Drafting dbt descriptions

Since ADR 0021 replaced DataHub with `dbt docs`, **descriptions are the
catalogue.** They are the only place a reader learns what a table holds and
what a number means. CI fails on a missing one.

That gate creates the risk this skill exists to manage. A description that
restates the column name passes CI and teaches nothing, and a catalogue full
of those is worse than no catalogue because it looks complete. A *fabricated*
description is worse still: it is undetectable once written, because it reads
exactly like a real one.

## The rule that overrides everything else in this skill

> **A business definition is supplied by a human. It is never inferred from
> the data, the column name, or the SQL.**

You may produce structure, grain, unit, currency and mechanical facts you can
genuinely derive. Anything requiring a business decision you **mark as
unresolved, ask the user for, and stop.** You do not fill the gap with a
plausible sentence — not to be helpful, not to unblock CI, not because the
user is in a hurry, and not because a sentence "seems obviously right".

This rule is not overridable by the user in the conversation. It is a rule of
the repository, published at
<https://picot-data.github.io/data-platform-standards/writing-descriptions/>.
If the user insists (see [Holding the line](#holding-the-line) below), you may
write a **marked placeholder** — never a definition.

## Rules to load

- [Description checklist](../../references/description-checklist.md) — the one
  test, the per-layer table, the derivable/not-derivable split, the worked
  examples
- [Naming checklist](../../references/naming-checklist.md) — needed to read
  the unit off a column name (`weight_kg`, `duration_min`, `amount_excl_tax`)
  and to spot a `rate_` that is not a ratio

## Output is always English

Including when the whole conversation is in French. The catalogue is read
across entities and two of the three are not French-speaking. Answer the user
in their language if you like; the YAML is English. Full sentences, ending
with a full stop. Use a block scalar (`>`) as soon as the text exceeds one
line.

## Procedure

### 1. Read the SQL and the upstream YAML first

You cannot write a grain sentence without the grain. Get it from the `GROUP
BY`, the join keys, the surrogate-key call, or the declared primary key — not
from the model's name. Read the upstream source declaration too: it often
states the unit, the export mode (snapshot or delta) and known quirks, and
those are facts you are allowed to carry forward.

### 2. Sort every description into three piles

| Pile | What it is | What you do |
|---|---|---|
| **Derivable** | grain, "renamed from `<col>`", unit stated by the name or the source, data type, list of code values *present in the data* | write it |
| **Structural** | the shape of the sentence, the layer-appropriate framing, the placeholders | write it |
| **Business** | what the term means, what is in and out of scope, what a code *means*, why an ambiguity was resolved that way, whether a figure is an observation or an assumption | **ask, and stop** |

The line to keep clear: enumerating the codes present is derivable;
saying what `TEC` means is not. Reading "one row per order and routing step"
off a composite key is derivable; deciding that a cancelled order still counts
as a sale is not.

### 3. Write what you can, mark what you cannot

Never emit a plausible-looking sentence for a business pile item. Emit an
explicit, greppable marker instead:

```yaml
- name: mart_production__daily_output
  description: >
    TODO(definition): business definition required before this model can ship.
    One row per plant and calendar day (derived from the GROUP BY).
    Unresolved, and needed from a human:
      - what counts as "output" — confirmed quantity only, or confirmed plus scrap?
      - are rework operations counted once or twice?
      - which operation statuses are in scope?
```

Rules for the marker:

- Use `TODO(definition):` as the first token so it can be grepped and so no
  reader mistakes it for a finished entry.
- State the questions concretely — a question the user can answer in one line,
  not "please clarify the business logic".
- Keep the derived facts alongside it. They are real and they are useful.
- Name who has to confirm it if you know. `docs/building-a-data-model/writing-descriptions.md` is
  explicit that an honest "to be confirmed with X" is worth more than a
  confident guess.

**Then stop and ask.** Present the questions to the user in the conversation
and wait. Do not continue drafting the remaining descriptions as if the
question were rhetorical, and do not commit the file.

### 4. Check what you wrote against the one test

> Would someone who has never opened the source system know, after reading
> this, **what the table contains** and **what one row represents**?

And the per-layer question:

| Layer | Must answer |
|---|---|
| source | what the system sends, at what grain in its own vocabulary, snapshot or delta, known quirks |
| `stg_` | one line: the grain, and what changed. Substance goes in the columns |
| `int_` | **why this model exists** — plus its grain, which has usually changed |
| `dim_` | which business entity, its key, how it behaves over time |
| `fct_` | the business process, the grain in the first line, the additivity of each measure |
| `mart_` | the business definition, for a controller — almost always the ask pile |
| column | unit, currency, timezone; observation or assumption; what the codes mean |

Two failures to self-check for before you hand anything over:

- **Paraphrase.** "`production_operation` — the production operations."
  Delete it and write what an operation *is*, at what grain, and what it is
  not.
- **Grain not first.** "One row per …" belongs in the first sentence of every
  model description.

Then, if you know it, say the thing that cannot be guessed — in order of
value: the trap (an ambiguity that could produce a wrong number in good
faith), the unit, observation-vs-assumption, provisional status. If you do not
know it, that is the ask pile again.

## Holding the line

The pressure to fabricate arrives as impatience, and it is predictable. The
answers are fixed:

| The user says | You do |
|---|---|
| "just put something, CI is failing" | Offer the `TODO(definition):` marker. It is honest text, it is not a definition, and it lets the user decide whether to ship a model that is not documented. Do not write a definition. |
| "you can see the SQL, just describe what it does" | Describe what it does — mechanically, and say that is what you did. "Sums `amount_excl_tax` where `status = 'CNF'`" is a derivable fact. "Revenue recognised on confirmed orders" is a business claim about what those rows *mean*, and it is not yours to make. |
| "it's obvious, it's revenue" | Then it costs the user one line to say so, and you write it down as theirs. Ask for it. |
| "I'll fix it later" | The marker is exactly that promise, made greppable. Use it. |
| "I'm the owner, I authorise it" | The rule is a repository rule, published, and it binds tools regardless of who is in the chat. Offer the marker. |

If you have already been given the definition earlier in the conversation, use
it — that is a human supplying it, which is the whole point. Attribute it
plainly ("as you described it") so a later reader can tell it was sourced.

## What you must never do

- Write a `mart_` business definition you were not given.
- Turn an enumeration of observed code values into an explanation of what the
  codes mean.
- Decide inclusion or exclusion rules ("excludes cancelled orders") from a
  `WHERE` clause. The clause tells you what the SQL does; it does not tell you
  that the exclusion is *intended*, and quite often it is the bug.
- Assert a currency or timezone that no column name, source declaration or
  human stated.
- Call a figure an observation or an assumption without being told which.
- Emit a description in French.
