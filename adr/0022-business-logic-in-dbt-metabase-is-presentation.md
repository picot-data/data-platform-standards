# ADR 0022: Business logic lives in dbt; Metabase is a presentation layer only

**Status**: Accepted

**Date**: 2026-08-18

## Context

This rule is already written down. [Metric definitions](../docs/building-a-data-model/metric-definitions.md)
states that metric logic never appears in a Metabase question, and
[BI and access](../docs/bi-and-access.md) states that Metabase models are
presentation — "scope, renaming, joins for convenience" — and that a Metabase
model several dashboards depend on should become a dbt model.

It is written down in the wrong kind of document. A documentation page is
rewritten whenever someone improves it, silently and without a record. An ADR can
only be undone by another ADR that says so and dates itself. The distinction
matters here more than almost anywhere else on the platform, for a reason specific
to this rule: **it is the one rule that cannot be restored once broken.**

Logic that leaks into a BI tool is invisible by construction. A `SUM` inside a
saved question is not in Git, is not tested, has no author in the history, and
appears in no inventory. After two years of self-service there is no way to
enumerate which figures on which dashboards were computed by Metabase rather than
read from a mart — the only way to find out is for two numbers to disagree in a
meeting, which is exactly the failure the platform exists to prevent. Every other
decision on this platform can be reversed by rewriting code that can be found.
This one cannot, because the code cannot be found.

[ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md) makes stating it urgent
rather than tidy. DataHub was the only component that would ever have observed
the boundary from outside — it ingests dashboard metadata and could have shown
that a dashboard reads a table. With the catalog reduced to dbt's own artifacts,
dbt knows nothing about Metabase unless it is told. The boundary therefore needs
a mechanism, not only a principle, and this ADR carries both.

## Options considered

1. **Leave it as documentation prose** — costs nothing today, and leaves the
   platform's least reversible rule in its most easily rewritten document.
2. **State it as a decision, and give dbt sight of the dashboards** — the rule
   becomes an ADR, and `dbt-metabase exposures` generates dbt `exposures:` from
   the live Metabase instance so that lineage reaches the dashboard.
3. **Enforce it technically, by exposing only marts to Metabase** — a real
   guarantee, obtained by making Metabase a viewer. Rejected: exposing dimensions
   and facts is what makes Metabase a self-service tool rather than a report
   renderer, and turning every new question into a modelling ticket would remove
   the reason the tool was chosen in [ADR 0008](0008-metabase-not-power-bi.md).

## Decision

Option 2. The boundary is a decision of record, and dbt exposures make the
dashboard side of it visible.

**The boundary.** Any calculation that encodes a business definition — a metric, a
ratio, a filter that decides what counts as a sale, a mapping of codes to
categories — lives in a dbt model, in Git, tested, described. Metabase may do four
things and no more: rename columns for readability, hide technical columns, join
for convenience where the join is trivial and carries no semantics, and scope a
question to a subset of rows.

The three re-aggregation rules in [Metric definitions](../docs/building-a-data-model/metric-definitions.md)
stay in force unchanged, and are the operational form of this decision:

1. never store a ratio or an average — store numerator and denominator, and let
   Metabase divide;
2. only additive measures may be rolled up, and the assumption must be verified
   rather than inherited;
3. metric logic never appears in a Metabase question.

**The escalation rule.** A Metabase model that more than one dashboard depends on
has stopped being presentation and become shared logic, whether or not it
contains arithmetic. It becomes a dbt model. This is the tripwire that catches
drift early, because the failure mode is not someone writing a `SUM` in defiance
of the rule — it is a convenience model quietly acquiring dependents.

**The mechanism.** `dbt-metabase exposures` runs on the entity VM, alongside the
`dbt-metabase models` push that [ADR 0017](0017-dbt-metadata-to-metabase-via-api.md)
already established, and its output is committed to the repository. Both
directions then use the same tool against the same instance: dbt descriptions go
out to Metabase, dashboard dependencies come back into dbt. The generated
`exposures:` are what let the catalog answer "which dashboard reads this table",
and — read in reverse — "which mart backs this figure".

Committing the output rather than generating it in CI is forced: reading the
Metabase API needs a credential, and the entity CI holds none by design. That
constraint is the reason for the staleness consequence below rather than an
oversight.

## Consequences

- **Lineage reaches the dashboard**, which is the question a steering committee
  actually asks. It is answered by clicking through the dbt docs site rather than
  by asking whoever built the dashboard what they remember.
- **Exposures can go stale, and a stale exposure is a false claim.** A dashboard
  deleted in Metabase stays in the committed `exposures:` until someone
  regenerates them, and the catalog will assert a dependency that no longer
  exists. This is strictly better than the current state — no lineage at all —
  but it is a known soft spot, and regeneration belongs in the same routine as
  the metadata push rather than in someone's memory.
- **Metabase's own models stay invisible to lineage.** They are not in Git and
  the exposures generator sees dashboards, not the models behind them. The
  escalation rule above is the only control on that blind spot, which is why it
  is part of the decision and not advice.
- **Some questions become a pull request.** A user who wants a figure the marts
  do not carry cannot simply write it in Metabase; the definition has to be added
  to a mart, tested and described. That is friction, deliberately, and it is the
  price of every figure in the group meaning one thing. Where the friction proves
  too high in practice, the answer is to widen what the marts expose — not to
  relax the boundary.
- **The rule now has to be superseded rather than edited.** The documentation
  pages continue to explain it, at length and with examples; this ADR is what
  they explain. Changing the boundary means writing ADR 0023 and saying why.
- Revisited if the self-service audience grows to the point where the pull
  request route becomes the bottleneck on answering business questions — at which
  point the change to consider is a governed semantic layer that Metabase can
  query, which [ADR 0015](0015-metrics-in-marts-not-metricflow.md) rejected only
  because MetricFlow could not be reached from Metabase, and not a loosening of
  this rule.
