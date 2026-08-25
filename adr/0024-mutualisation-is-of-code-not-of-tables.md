# ADR 0024: Mutualised transformations are shared as code, not as tables

**Status**: Accepted

**Date**: 2026-08-25

## Context

[ADR 0011](0011-shared-terraform-module-and-entity-template.md) removed
copy-paste from three artefacts — the Terraform module, the mono-repo skeleton,
and the CI workflow — on one argument: if they live inside each entity repo,
"the second entity onboarded is a fork of the first, and a fix made for `dti`
never reaches `bg` unless someone remembers to port it by hand".

The dbt model layer was not one of the three, and nothing replaced it. The
template repository ships **no models**: its `transformation/` holds
`dbt_project.yml`, a `packages.yml` naming only `dbt_utils`, and one macro. A
second entity created by "Use this template", as
[Onboarding a new entity](../docs/onboardings/onboarding-a-new-entity.md) step 5
prescribes, therefore starts with an empty project — and its `int_`, `dim_`,
`fct_` and `mart_` models can only arrive by copying the reference entity's.

That is the fork ADR 0011 rejected, occurring in the one layer that carries
business definitions rather than infrastructure. It also makes
[ADR 0015](0015-metrics-in-marts-not-metricflow.md) imprecise:
[Metric definitions](../docs/building-a-data-model/metric-definitions.md) says a
metric is defined once, in a `mart_` model. "Once" was written when the platform
had one entity. Across N entity repositories it means once *per entity*, which is
the condition that page opens by describing as the failure to prevent.

### Two questions that must not be conflated

- **Sharing code** — one definition of a transformation, compiled into each
  entity's own warehouse, producing that entity's own tables.
- **Sharing tables** — one physical `fct_order` holding several entities' rows,
  discriminated by an `entity` column and unioned into a group database.

This ADR decides the first and **not** the second. The distinction matters
because the POC implements the second, and it is scaffolding: the `entity`
column, the `gold_group` union and the entity-salted surrogate keys were built to
demonstrate Metabase's access partitioning to a steering committee, using a
fabricated second entity. Production is separate sources, separate models and a
clear separation per entity. Any argument for shared code that rests on the union
therefore rests on something production will not have.

That matters for the risk assessment, in both directions:

- **Severity is lower than the union suggests.** Two entities computing revenue
  from two copies of the SQL produce two numbers, each defensible on its own terms
  and not comparable — not one wrong figure that nobody can challenge because a
  union silently summed two different definitions.
- **Detectability is zero.** With one physical table, two incompatible schemas
  eventually collide and something errors. With separate tables, nothing anywhere
  breaks when two copies drift: no conflict to raise, no failing test, no column
  turning to NULL. The drift is found by a person noticing.

There is also a simplification worth recording, because it inverts an assumption
easy to carry over from the POC: **sharing code is cleaner without shared
tables.** If each entity's warehouse holds only its own rows, a shared model needs
neither an `entity` discriminator nor surrogate keys salted with the entity code.
Both exist solely to keep several entities apart inside one table.

### Why the package cannot simply be built now

A conformed layer is observed, not decreed. Only Dirickx's SAP has been modelled.
B&G's configuration, its order types, and whether its order grain matches at all
are unknown. A shared `fct_order` written today would be Dirickx's model with a
general-sounding name, and the first contact with the second SAP would break it —
at the point of maximum cost, with an entity mid-onboarding. The POC does run one
project twice over an `entity_code` variable, but against fixtures built for a
demonstration: that establishes the models tolerate an entity variable, not that
two real ERP configurations share a grain.

So the decision needed is not *whether* to deduplicate the model layer, which
ADR 0011 already settled in principle and which the platform owner has stated as
the goal — everything mutualizable in a common repository, imported by each
entity repository — but how to sequence it without the deferral quietly becoming
permanent.

## Options considered

1. **Leave the models copied per entity, indefinitely.** Costs nothing today, and
   permanently accepts N definitions of every metric in the one layer where a
   definition is the product.
2. **Create the shared package now, before B&G is modelled.** The guarantee is
   immediate, and the conformed layer would be an invented abstraction discovered
   to be wrong at the worst possible moment.
3. **Share the entire transformation project — one dbt project with per-entity
   staging folders (`models/staging/dti/`, `models/staging/bg/`), selected at
   run time.** The strongest possible guarantee, since there would be exactly one
   copy of every conformed model and no version skew between entities. Genuinely
   simpler than a package at today's scale, and rejected on one ground only: it
   requires shared write access across entities, which is the isolation
   [ADR 0002](0002-caf-landing-zone-structure.md) and
   [Repositories and delivery](../docs/repositories-and-delivery.md#why-one-repo-per-entity-not-one-mega-mono-repo-for-the-whole-group)
   deliberately keep. Worth reopening if that isolation is ever judged
   theoretical.
4. **No shared code; a group glossary alone.** Each entity implements the group's
   written definition its own way. This is the right mechanism where two models
   genuinely cannot converge, but as the *only* mechanism it leaves N
   implementations of one definition.
5. **Two phases: identical copies now, extraction into a shared package on a named
   trigger, with a guard rail that keeps the extraction mechanical.**

## Decision

Option 5, with option 4 as its companion rather than its alternative.

**Mutualisation is of code, not of tables.** One definition lives in one file and
is compiled into each entity's own warehouse, producing that entity's own tables.
No `entity` column is required, no union is performed, no group table is created.
What is shared is provenance, never storage.

**The destination.** `data-platform-dbt-core`, consumed by each entity's
`packages.yml` at a pinned revision — the same live reference ADR 0011 gave the
Terraform module. It holds the mutualised models together with their
`description:` blocks and their tests, because a definition separated from its
documentation and its tests is not a shared definition.

**What counts as mutualizable is a test, not a list.** A transformation is
mutualizable when its logic does not depend on which entity's source it reads.
Macros, generic tests and `dim_date` pass that test immediately. `int_`, `dim_`,
`fct_` and `mart_` models are judged **per model**, once both entities have been
modelled — not per layer, and not in advance.

**The boundary.** `staging/` stays in the entity repository. That is where two SAP
configurations legitimately differ, and keeping it local is what stops entity
specificity from climbing into the shared models. The package's models `ref()`
staging models by name, so staging becomes an explicit contract — deliberately,
since it forces divergence downward into the layer built to absorb it.

**Genuine business divergence is declared, never forked.** Where two entities
really do differ, the difference becomes a `var()` read by the shared model and
set in the entity's `dbt_project.yml`. Copying a shared model into an entity
repository to modify it is the thing this ADR exists to prevent, and it is not an
escape hatch.

**Two phases.**

1. **Identical models, copied definitions.** Each entity's repository carries its
   own copy, written to be the same. The assumption that the figures mean the same
   thing is accepted rather than proven.
2. **Extraction.** What proved mutualizable moves into `data-platform-dbt-core`
   and is imported by each entity repository.

**Phase 1's assumption is made falsifiable, cheaply.** Telling ourselves the
figures mean the same thing is an assumption, and the way to stop it being a
silent one is to write each group-level definition down once and have every
entity's `mart_` description state that it implements that definition. This is the
**precondition** for phase 2, not a substitute: a shared model cannot be extracted
until both sides agree the definition was shared. It is also the only thing that
makes phase 1 auditable while it holds.

**The guard rail: the naming convention binds across entities, and it is the only
control.** Same model names, same column names, same units
([Column naming](../docs/naming-conventions.md#column-naming)). This is the whole
difference between an extraction that is a file move and one that is a rewrite
dragging every Metabase question behind it. It is checked in each entity's pull
requests, because with no union there is nothing behind it and no later moment at
which a breach announces itself.

**The trigger.** Extraction happens once the second entity's Gold layer exists and
passes its tests, and in any case **before a third entity is onboarded**. Three
copies are worse than two in a way that is not proportional: they make "which one
is right" a question with no majority answer.

**Out of scope, deliberately.** Whether a group-level serving concept exists in
production at all — a group naming convention, a group database, or nothing — is
not decided here. Answering it by inertia from the POC's `gold_group` is a
specific mistake this ADR exists to prevent.

## Consequences

- **Divergence is possible during phase 1, and that is the accepted price of not
  inventing the conformed layer.** It surfaces as two visible numbers rather than
  one invisible wrong one, which is a materially smaller exposure than a shared
  table would carry.
- **Nothing detects that divergence automatically.** No union to collapse, no
  schema to conflict, no test to fail. Phase 1 rests entirely on the naming
  convention holding and the group definitions being written down. Neglect both
  and the drift is discovered by someone noticing, at an unpredictable moment —
  the platform's original failure mode, reintroduced.
- **The extraction is mechanical only if the guard rail actually held.** If it did
  not, this decision failed at the moment of drift and nobody finds out until the
  merge. That is why it belongs in pull request review rather than in a checklist
  consulted at extraction time.
- **The serving topology is untouched.** The package shares the file, not the run:
  each entity's VM still builds every model into its own DuckDB file and publishes
  it under its own prefix. Per-entity serving databases remain the access
  boundary, because Metabase's open-source edition has no row-level security and
  the finest grain it can grant or deny is a database
  ([ADR 0016](0016-central-metabase-not-per-entity.md)).
- **The catalog stays per entity.** Each entity's CI keeps building its own dbt
  docs site ([ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md),
  [ADR 0023](0023-catalog-served-from-the-shared-bi-vm.md)); shared models appear
  in every site with byte-identical descriptions because they come from one file.
  This is **one source of definitions and N views**, not one governance view.
  Cross-entity lineage and a single group catalog stay out of scope, as ADR 0021
  decided.
- **Shared models will be simpler than the POC's.** No `entity` column, no
  entity-salted surrogate keys, no `SELECT DISTINCT` undoing a union's
  duplication. Anything carried over from the POC's models should be re-examined
  for machinery that only existed to keep entities apart inside one table.
- **Version skew is more dangerous here than for Terraform.** ADR 0011 accepts
  `dti` on `v1.2.0` and `bg` on `v1.3.0` as a feature. For infrastructure it is;
  for a metric it means the group has two definitions of revenue until the lagging
  entity bumps. Entities may differ on the module `ref`; they should be bumped
  together on the package, and a skew left standing needs the same justification
  as a divergence.
- **Two reference pages currently describe the POC's scaffolding as the group's
  data model.**
  [Data layers — multi-entity tables](../docs/building-a-data-model/data-layers.md#multi-entity-tables)
  and [Onboarding a new entity](../docs/onboardings/onboarding-a-new-entity.md)
  step 6 present the `entity` column and the shared table as the standard. They
  describe the demonstration and must say so, or the next engineer to onboard an
  entity will merge two unrelated models into one table.
- **Group comparability is left unresolved, and it is the question a steering
  committee will ask.** With separate sources, separate models and no shared
  table, "what is the group's revenue" is answered by adding two independently
  computed numbers. The group definitions above make that defensible; they do not
  make it automatic.
- Revisited if the two entities' Gold layers turn out to share almost nothing, in
  which case the package shrinks to macros, tests and `dim_date` and the group
  definitions carry the whole burden — or if a third entity is onboarded before
  the trigger fires, at which point the extraction stops being mechanical and its
  cost has to be re-estimated before it is scheduled.
