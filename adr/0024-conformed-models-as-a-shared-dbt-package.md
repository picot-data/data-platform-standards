# ADR 0024: Conformed models move to a shared dbt package, once the conformed layer has been observed

**Status**: Accepted

**Date**: 2026-08-25

## Context

[ADR 0011](0011-shared-terraform-module-and-entity-template.md) removed
copy-paste from three artefacts — the Terraform module, the mono-repo skeleton,
and the CI workflow — on one argument: if they live inside each entity repo,
"the second entity onboarded is a fork of the first, and a fix made for `dti`
never reaches `bg` unless someone remembers to port it by hand".

The dbt model layer was not one of the three, and nothing replaced it. The
template repository ships **no models at all**: its `transformation/` holds
`dbt_project.yml`, a `packages.yml` naming only `dbt_utils`, and one macro. A
second entity created by "Use this template", as
[Onboarding a new entity](../docs/onboardings/onboarding-a-new-entity.md) step 5
prescribes, therefore starts with an empty project — and its `stg_`, `dim_`,
`fct_` and `mart_` models can only arrive by copying the reference entity's.

That is precisely the fork ADR 0011 rejected, occurring in the one layer that
carries business definitions rather than infrastructure. It also makes
[ADR 0015](0015-metrics-in-marts-not-metricflow.md) imprecise:
[Metric definitions](../docs/building-a-data-model/metric-definitions.md) says a
metric is defined once, in a `mart_` model. "Once" was written when the platform
had one entity. Across N entity repos it means once *per entity*, which is the
condition that page opens by describing as the failure to prevent.

**The divergence would be invisible, and that is what forces a decision now
rather than at the second entity.** The group serving database is built by
unioning each entity's published Parquet with `union_by_name = true`. Two
`revenue` columns maintained in two repos stack into a single column named
`revenue`, which Metabase sums; a column renamed in one entity arrives as NULL
rather than as an error. The union removes the only signal that would otherwise
have exposed the drift — two people arriving at a meeting with two different
numbers. It replaces it with one number that is wrong and unchallenged.

The obvious response is to declare the shared package immediately. It is not
available: a conformed layer is observed, not decreed. Only Dirickx's SAP has
been modelled. B&G's configuration, its order types, and whether its order grain
matches at all are unknown. A shared `fct_order` written today would be
Dirickx's model with a general-sounding name, and the first contact with the
second SAP would break it — at the point of maximum cost, with an entity
mid-onboarding. The POC does run one project twice over a `entity_code`
variable, but against fixtures built for a steering-committee demonstration:
that establishes the models tolerate an entity variable, not that two real ERP
configurations share a grain.

So the decision needed is not *whether* to deduplicate the model layer, which
ADR 0011 already settled in principle, but how to defer it for the one reason
that justifies deferring it, without the deferral quietly becoming permanent.

## Options considered

1. **Leave the models copied per entity, indefinitely.** Costs nothing today,
   and permanently places the platform's least visible divergence in the one
   layer where the group union hides it.
2. **Create the shared package now, before B&G is modelled.** The guarantee is
   immediate, and the conformed layer would be an invented abstraction
   discovered to be wrong at the worst possible moment.
3. **Share the entire transformation project — one dbt project, run once per
   entity.** The strongest possible guarantee, since there would be exactly one
   file. Rejected: staging is where two SAP configurations legitimately differ,
   so `stg_sap__order` would accumulate per-entity Jinja branches, and the
   sharpest form of entity-specific logic would end up in the shared repository.
4. **Keep the copies and detect divergence with a comparison test rather than
   preventing it.** Rejected as a substitute: it needs somewhere to run that
   sees both entities' Gold data, and entity VMs see only their own and are
   deallocated outside their window
   ([ADR 0018](0018-scheduled-start-stop-for-entity-vms.md)); and a detector
   that fires after a group figure has been published has prevented nothing.
5. **Model each entity separately, then extract the observed common layer into a
   shared package on a named trigger, with guard rails that keep the extraction
   mechanical.**

## Decision

Option 5.

**The destination.** A shared dbt package repository,
`data-platform-dbt-core`, consumed by each entity's `packages.yml` with a
pinned git `revision` — the same mechanism, and the same versioning discipline,
that ADR 0011 gave the Terraform module. It holds `intermediate/`,
`dimensions/`, `facts/` and `marts/`: the SQL, the `description:` blocks and the
tests together, because a definition separated from its documentation and its
tests is not a shared definition.

**The boundary.** `staging/` stays in the entity repository. That is where two
SAP configurations legitimately differ, and keeping it local is what stops
entity specificity from climbing into the shared models. The package's `int_`
models `ref()` staging models by name, so the staging layer becomes an explicit
contract — deliberately, since it forces divergence downward into the layer
built to absorb it.

**Genuine business divergence is declared, never forked.** Where two entities
really do differ — an order type that counts as a sale for one and not the other
— the difference becomes a `var()` read by the shared model and set in the
entity's `dbt_project.yml`. One definition with a declared parameter, not two
definitions. Copying a shared model into an entity repo to modify it is the
thing this ADR exists to prevent, and it is not an escape hatch.

**Sequencing.** Each entity is modelled in its own repository until its Gold
layer exists and its tests pass. The conformed layer is then whatever is
*observed* to be common across the two, not what was hoped before either was
built.

**Guard rail 1 — the naming convention binds across entities.**
[Naming conventions](../docs/naming-conventions.md#column-naming) is a contract
between entities for the duration of the separation, not a style guide: the same
model names, the same column names, the same units — `amount_excl_tax`,
`date_order`, `customer_sk`, `qty_ordered`. This is the whole difference between
an extraction that is a file move and one that is a rewrite dragging every
Metabase question behind it. It costs nothing while separated, and it is checked
at each entity's pull request, not at merge time.

**Guard rail 2 — `gold_group` carries no `mart_` while the marts are copies.**
Facts and dimensions may be unioned: they carry raw measures, and a divergence
in them surfaces as two comparable numbers. A mart carries a definition, and
`union_by_name` collapses two definitions into one column without a signal.
Nothing computed twice, from two files, is published as a group figure.

**The trigger.** Extraction happens before the first group-level dashboard is
published, and in any case before a third entity is onboarded — not "when there
is time". Three copies are more than fifty percent worse than two: they make the
question "which one is right" have no majority answer.

## Consequences

- **Divergence is possible during the separation window, and that is the
  accepted price of not inventing the conformed layer.** Guard rail 2 bounds it
  to figures nobody has published as a group figure, which is the difference
  between a discrepancy that costs a reconciliation and one that costs a
  steering committee's trust.
- **The extraction is mechanical only if guard rail 1 actually held.** If it did
  not, this decision has already failed at the moment of drift and nobody will
  find out until the merge. That is why it belongs in pull request review rather
  than in a checklist consulted at extraction time — it is the guard rail that
  fails silently.
- **The serving topology does not change.** The package shares the definition,
  not the run: each entity's VM still builds its own copy of every model into
  its own DuckDB and publishes it under its own `gold/company_<code>/` prefix.
  `gold_dti`, `gold_bg` and `gold_group` all continue to carry
  `mart_sales__daily_orders`. Per-entity serving databases exist because
  Metabase's open-source edition has no row-level security and the finest access
  grain it offers is the database
  ([ADR 0016](0016-central-metabase-not-per-entity.md)); sharing definitions
  does not touch that and never will.
- **The catalog stays per entity.** Each entity's CI keeps building its own dbt
  docs site ([ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md),
  [ADR 0023](0023-catalog-served-from-the-shared-bi-vm.md)); shared models appear
  in every site with byte-identical descriptions because they come from one
  file. This produces **one source of definitions and N views**, not one
  governance view. Cross-entity lineage and a single group catalog remain out of
  scope, as ADR 0021 decided.
- **Version skew between entities is more dangerous here than for Terraform.**
  ADR 0011 accepted `dti` on `v1.2.0` and `bg` on `v1.3.0` as a feature. For
  infrastructure it is; for a metric it means the group genuinely has two
  definitions of revenue until the lagging entity bumps. Entities may differ on
  the module `ref`; they should be bumped together on the package, and a skew
  left standing needs the same justification as a divergence.
- **The reference documentation now understates the problem in two places.**
  [Data layers — multi-entity tables](../docs/building-a-data-model/data-layers.md#multi-entity-tables)
  says "same table, same structure, no duplication", which is true of the unioned
  result and false of the models producing it; and
  [Onboarding a new entity](../docs/onboardings/onboarding-a-new-entity.md)
  steps 5 and 6 say where an entity's repository comes from and where its rows
  land, but not where its models come from. Both need to state which side of the
  boundary they describe.
- **Some of what looks conformed will turn out not to be.** If the two SAP
  configurations share almost nothing at Gold grain, the package shrinks to
  `dim_date` and the metric definitions, and the guarantee has to be sought
  through contract tests over comparable measures instead. That outcome is
  information, not failure — but it is a different decision and would need its
  own ADR.
- Revisited if a third entity is onboarded before the trigger fires, or if
  either guard rail is found to have been breached — in both cases the
  extraction stops being mechanical and its cost has to be re-estimated before
  it is scheduled rather than after.
