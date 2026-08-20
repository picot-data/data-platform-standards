# Onboarding a data analyst

For the person who builds questions and dashboards in Metabase. It assumes no
knowledge of dbt, Azure or git, and it is the only page on this site written for
someone who will never open the repository.

If you administer the instance rather than build in it, read
[BI and access](bi-and-access.md) instead.

## What you can do

You are in `<entity>_analysts`. That gives you, on your entity's data:

- the **query builder** and **native SQL**
- the right to **create and publish** anywhere in your entity's collections,
  including next to certified dashboards

There is no approval step in the tool. The rules below are what makes that
workable, and the last one — knowing when a calculation stops being yours to
make — is the one that matters.

You see one database, `gold_<entity>`, holding your entity's data. Comparing
entities uses `gold_group`, which is a separate database and a separate
permission. There is no filter to switch between them: separate databases are
how entity isolation is enforced.

## Where things go

```
Dirickx
  Sales            ← published, read by others
  Production
  Explorations     ← work in progress, invisible to readers
Your personal collection   ← drafts, invisible to everyone
```

- **Personal collection** — your scratchpad. Use it freely; nobody else sees it.
- **`Explorations`** — work you want a colleague to look at, but that nobody
  should rely on. Readers cannot open this collection at all.
- **Domain collections** (`Sales`, `Production`, …) — published content. Filed by
  business domain, never by department: a sales dashboard is read by sales,
  finance and management alike.

You may write straight into a domain collection. Going through `Explorations`
first is a habit, not a gate — and it is the habit that keeps the domain
collections worth trusting.

## Four rules for writing questions and dashboards

**1. The name is the documentation.** `CA mensuel par région — 12 derniers mois`,
not `Question 4`. Say the measure, the breakdown and the period. Somebody will
find this in a search box six months from now with no other context.

**2. Prefer the query builder to SQL when both would work.** A question built in
the query builder stays explorable: a reader clicks "view these records", changes
a grouping, drills into a bar. A SQL question is a black box — it answers exactly
one question and nothing around it. You have SQL because you need it to
investigate and to demonstrate; that is not a reason to publish with it.

**3. One dashboard, one intention. Seven cards maximum.** Past that, the reader
stops reading and starts scrolling. A dashboard that needs more cards is two
dashboards that have not been separated yet.

**4. Give readers something to turn.** Readers cannot create anything, so a
dashboard without filter widgets is a dead end for them: the only way to see
another month or another region is to ask you. Add the filters — period, entity,
category, whatever the question naturally varies by — and wire them to every card
they apply to. This is what makes the reader tier usable rather than a
restriction.

## When a question has to become a dbt model

Metabase is for **presentation**. The definition of a business figure lives in
the transformation layer, versioned, tested and documented
([ADR 0022](adr-index.md)). The boundary is not "does it calculate" — aggregating
is what a BI tool is for. The boundary is **does it decide**.

### Always fine in Metabase

Filtering, sorting, limiting to a top 10, renaming a column for display, hiding
technical columns, choosing the chart and the number format, and **summing or
counting a measure that is already defined** over a period or a breakdown you
choose.

### Always a dbt model

- a **ratio or a rate** — anything divided by anything
- a **filter that decides what counts** — excluding cancelled orders is a
  definition of what a sale is, not a display choice
- a **mapping of codes to labels**, or a `CASE` that invents a category
- a **join** that is not already modelled
- a measure that **cannot be summed** — a rate averaged over a period is not the
  rate of the period

### Three questions when you are unsure

1. **Does it decide something?** If the number depends on a rule that exists only
   inside this question, that rule needs a home.
2. **Would a second dashboard need the same calculation?** Then it will be
   written twice, and the two copies will disagree.
3. **If someone challenges the figure in a meeting, where is the answer?** If it
   is only visible by opening your question, it is not documented.

In one sentence: **if you have to explain your SQL for the number to be
understood, a dbt model is missing.**

## Asking for a model

This is a conversation, not a ticket. Bring:

- **the working question**, in `Explorations`, marked 🚧
- **what the figure means, in one sentence, in business terms.** Not the SQL —
  the meaning. "Scrap rate is scrapped quantity over quantity produced, per
  work centre and per day."
- **what is included and what is excluded**, and why. Usually the interesting
  part: rework, cancelled orders, one plant, a currency.
- **who reads it** and how often

That sentence is not a formality. It becomes the model's description, which is
the glossary entry the whole group reads — so it is written by you, the person
who knows the business, and never guessed by whoever builds the model. If the
definition cannot be stated in a sentence, the calculation is not ready to be
published, and that is a useful thing to discover before it is on a screen.

What happens then: the model is built, tested and documented; you rebuild your
question on top of it, which is usually simpler than the original; and it can
carry a ⭐.

## Markers

Exactly one marker, at the start of the name, on questions and dashboards only —
never on collections.

| Marker | Meaning |
|---|---|
| ⭐ | Certified: reviewed, the models behind it pass their tests, an owner is named in the description |
| 🚧 | Work in progress, figures may be wrong. Lives in `Explorations` |
| ⛔ | Deprecated: do not build on it. The replacement is linked in the description |

No marker means ordinary content: usable, not certified. A ⭐ dashboard whose
models start failing their tests loses the star before anyone asks — certification
is a statement about now, not about the day it was reviewed.

Only certified content is pinned. Pinning and ⭐ go together, so the two signals
never contradict each other.

## When a number looks wrong

Say so, and **do not fix it in Metabase.** A correction applied inside a question
fixes one screen and leaves every other use of the same figure wrong, with no
trace of the disagreement. If the figure comes from a model, the fix belongs in
the model, where it reaches everything at once and gets a test so it cannot come
back.

## Related

- [BI and access](bi-and-access.md) — the instance, groups and permissions
- [Glossary](glossary.md) — what the group's business terms mean
- [Metric definitions](metric-definitions.md) — where a figure is defined and why
  only once
