# BI and access

How Metabase is organised, and who is allowed to see what. The reasoning behind
the central instance is in
[ADR 0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md);
the reasoning behind where its table metadata comes from is in
[ADR 0017](https://github.com/picot-data/data-platform-standards/blob/main/adr/0017-dbt-metadata-to-metabase-via-api.md).

Metabase is the group's only BI tool — see
[ADR 0008](https://github.com/picot-data/data-platform-standards/blob/main/adr/0008-metabase-not-power-bi.md).
Everything on this page assumes the **open-source edition**, whose limits shape
several of the rules below.

## One instance for the group

Metabase runs once, on `vm-picot-shared-bi-weu-01` in
`rg-picot-shared-data-weu`, not on the entity VMs. Entity VMs run the pipeline
up to Gold; the shared VM reads Gold. A group-level dashboard comparing entities
is the reason the platform exists, and it can only exist in one instance that
sees every entity.

The catalog is served from that machine too, at `/catalog/<entity>/` — not because
it needs a machine of its own, but because this is the only one always on
([ADR 0021](https://github.com/picot-data/data-platform-standards/blob/main/adr/0021-dbt-docs-not-datahub-as-the-catalog.md)
for why dbt docs,
[ADR 0023](https://github.com/picot-data/data-platform-standards/blob/main/adr/0023-catalog-served-from-the-shared-bi-vm.md)
for why here). It is a static site, so serving it costs a web server and no
application.

Three operational rules follow from centralising:

- **The application database is Postgres, not H2.** This is Metabase's own
  store of users, groups, permissions, saved questions and dashboards — nothing
  to do with the analytics data, which lives in DuckDB. H2 is acceptable for a
  single throwaway instance and not for the system holding the group's access
  rules.
- **Nothing entity-specific is installed on the shared VM.** No dbt project, no
  Dagster, no ingestion. Its jobs are Metabase, the catalog, and the refresh
  below — which pulls the dbt docs site along with the Gold Parquet.
- **This VM is never on a start/stop schedule**, unlike the entity VMs
  ([ADR 0018](https://github.com/picot-data/data-platform-standards/blob/main/adr/0018-scheduled-start-stop-for-entity-vms.md)).
  It serves people during working hours; that is the opposite workload.

### How Gold reaches Metabase

A scheduled refresh on the BI VM pulls the published Gold Parquet files from
ADLS to local disk, then rebuilds one serving DuckDB database per scope as
views over those local files.

Metabase never queries `abfss://` directly. DuckDB is an embedded engine that
requests a fresh Entra token per remote operation, and the instance metadata
service throttles those at roughly five per second — the failure mode
[ADR 0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md)
documents in detail. A dashboard refreshing on every page view would reproduce
it exactly.

The refresh is a **pull on a schedule**, not a push from each entity's Dagster
run. A push would need N sets of credentials reaching across the landing-zone
boundary, and would leave `gold_group` owned by whichever entity's pipeline
happened to finish last.

Consequence to state on dashboards rather than hide: Metabase lags the pipeline
by up to one refresh interval. Every dashboard surfaces the `_loaded_at` of its
underlying data.

### Databases in Metabase

One Metabase database per scope. This is the mechanism that makes entity
isolation enforceable — see [Data permissions](#data-permissions).

| Metabase database | Serving file | Built from |
|---|---|---|
| `gold_dti` | `serving_dti.duckdb` | `gold/company_dti/*.parquet` |
| `gold_bg` | `serving_bg.duckdb` | `gold/company_bg/*.parquet` |
| `gold_group` | `serving_group.duckdb` | every `gold/company_*/` folder, unioned by name |

`gold_group` holds the same tables with rows from every entity, distinguished by
the `entity` column — see
[Data layers](data-layers.md#multi-entity-tables). It is not a different data
model, only a wider selection of rows.

**Delete Metabase's Sample Database.** From version 63 it is a SQLite file, and
leaving it connected means a query editor silently pointed at it fails with
`[SQLITE_ERROR] ... no such table`, naming a table that exists in a different
database. Removing it eliminates the whole class of confusion.

## Collections

Collections are **both** the filing system and the unit of content permission.
The structure is therefore chosen so that the permission boundary sits at the
top level, where it can be stated once and inherited.

**Entity first, business domain second.**

```
Group                    ← cross-entity, gold_group
  Sales
  Finance
Dirickx                  ← dti, gold_dti
  Sales
  Finance
  Production
  Quality
  Explorations
B&G                      ← bg, gold_bg
  ...
Platform                 ← pipeline health, data quality, usage
```

Entity first because it is the security boundary, and collection permissions are
inherited by sub-collections: one grant at the top instead of one per domain.

Domain second — **not** service or department. The domains are the same list
that names marts (`sales`, `finance`, `production`, `quality`, `hr` — see
[Naming conventions](naming-conventions.md#dbt-model-naming)), so a dashboard and
the mart behind it are filed under the same word. Three reasons not to file by
service:

| Filing by domain | Filing by service |
|---|---|
| A sales dashboard is read by sales, finance and management alike | The same dashboard is invisible to two of them, or duplicated |
| Domains outlive reorganisations | A department can merge or be renamed next year |
| The department is a *permission* axis, expressed as a group | Two axes collapsed into one, and neither works cleanly |

`Explorations` exists in every entity to hold what is not validated, so that the
domain collections stay trustworthy. **Personal collections** are the place for
drafts; encourage them rather than tolerating drafts in shared collections.

Sub-collections below the domain are added only when a domain passes roughly
fifteen questions — a `Building blocks` sub-collection for the questions that
exist to feed dashboards. Creating that depth up front buys nothing.

## Certification markers

The open-source edition has no *Verified* badge and no *Official collection* —
both are paid features. The signal of trustworthiness is therefore a naming
convention, and it is worth nothing unless it is applied strictly.

**Exactly one marker, at the start of the name, on dashboards and questions
only.**

| Marker | Meaning | Who may apply it |
|---|---|---|
| ⭐ | Certified: reviewed, the underlying models pass their dbt tests, an owner is named in the description | Analysts and above only |
| 🚧 | Work in progress — figures may be wrong. Lives in `Explorations` | Anyone |
| ⛔ | Deprecated: kept for reference, do not build on it. A replacement is linked in the description | Analysts and above only |

Anything with no marker is ordinary content: usable, not certified.

Rules that keep the convention meaningful:

- **Never on collection names, and never on dbt models.** Collections appear in
  URLs and navigation; dbt names are bound by
  [Naming conventions](naming-conventions.md#general-rules), which allows no
  special characters.
- **Pinning and ⭐ go together.** Pinning is Metabase's own prominence
  mechanism; only certified content is pinned, so the two signals never
  contradict each other.
- **The marker is a claim, not a control.** Nothing in Metabase stops a viewer
  from typing a star into a name of their own. What makes it credible is that
  only analysts can write into the domain collections at all — the marker rides
  on the collection permission, it does not replace it.
- A ⭐ dashboard whose models start failing their tests loses the star before
  anyone asks. Certification is a current statement, not a historical one.

## Groups

Two axes, and both are needed: **entity** decides which data, **tier** decides
what a person may do with it. Three tiers per entity, named after the capability
they carry rather than after a job title — a title invites debate about who
deserves it, a capability does not.

| Group | Capability | Typical member |
|---|---|---|
| `Administrators` | Built in — everything. Do not create a second admin group | platform owner |
| `<entity>_analysts` | Native SQL, and **Curate** on their entity's collections: they publish | controller, power user |
| `<entity>_explorers` | Query builder only, no SQL. Build and save their own questions | anyone comfortable with self-service |
| `<entity>_readers` | Consume only: open dashboards, filter, drill in. No question of their own | occasional consumer |
| `group_analysts` | `<entity>_analysts`, across every entity plus the group scope | group-level controlling |
| `platform_automation` | **Not a group to create.** The metadata sync's API key has to sit in `Administrators` — see [The automation key](#the-automation-key) | — |

Group names are `snake_case`, and `<entity>` is the same entity code used
everywhere else — Azure resource names, the `entity` column, ADLS prefixes (see
[Azure landing zones](azure-landing-zones.md#resource-naming-pattern)).

Two naming choices worth knowing the reason for:

- **`readers`, not `viewers`.** Metabase's own collection permission levels are
  *Curate* / *View* / *No access*, and the explorers tier also holds *View*. A
  group called `<entity>_viewers` would therefore describe two tiers, in the
  exact screen where the distinction matters.
- **`analysts` at both scopes.** `dti_analysts` and `group_analysts` are the
  same capability at two scopes, and the parallel names say so.

**Create only the groups an onboarded entity needs.** Three per entity, plus the
three fixed ones. Do not pre-create groups for entities that are not yet
onboarded, and do not create a group per department: a department that must not
see a figure gets a restricted sub-collection, not a group of its own.
Multiplying groups is what makes a Metabase instance unmaintainable, and a
person's effective rights are the *most permissive* of their groups — so every
extra group is an extra way to be wrong.

**Start people one tier lower than they ask for.** Promoting someone is a
two-click change; discovering that a dashboard everyone relies on was built by
someone who did not know the model is not.

Group membership is maintained by hand in Metabase. Automatic mapping from an
identity provider (SAML/JWT) is a paid feature, which is a further reason to
keep the number of groups small.

## Data permissions

**Data permissions and collection permissions are independent, and both are
required.** This is the mistake to avoid: a group with data access to a database
can browse every table in it regardless of collections. Collections hide *saved
content*; they never hide *data*.

**Strip `All Users` of data access before granting anything else.** Until that
is done, every grant below is decorative, because rights are cumulative across
groups.

The *Create queries* setting is what separates the three tiers.

| Group | `gold_dti` | `gold_bg` | `gold_group` |
|---|---|---|---|
| `dti_analysts` | View data + **query builder and native SQL** | No access | No access |
| `dti_explorers` | View data + **query builder only** | No access | No access |
| `dti_readers` | View data + **Create queries: No** | No access | No access |
| `bg_analysts` / `bg_explorers` / `bg_readers` | No access | same three tiers on `gold_bg` | No access |
| `group_analysts` | View data + query builder and native SQL | same | same |

Why the tiers fall where they do:

- **Native SQL is an analyst right** because a SQL question is opaque to its
  readers and cannot be re-explored in one click — someone publishing one takes
  on the job of explaining it.
- **The explorers tier is the point of the platform.** Supervised self-service
  is the value being delivered; what must be locked down is the *scope of data*,
  not curiosity. Most people belong here, not in `readers`.
- **`readers` exists for consumers, not as a punishment.** Someone who opens one
  dashboard a month gains nothing from a query builder and is better served by
  an interface that offers only what they need.

One thing to verify in your instance rather than assume: *Create queries: No*
also removes the ability to drill through a chart into the underlying rows,
because a drill-through is an ad hoc query. If that turns out to matter for
readers, the answer is to move them to `explorers` — not to loosen the data
scope.

**There is no row-level filtering in the open-source edition.** Row and column
security is paid, so the finest free grain is the database — which is exactly
why there is one serving database per entity. A single database plus a filter on
the `entity` column would be a convention a user could bypass, not a boundary.
If a requirement ever appears for finer separation *within* an entity, it needs
a decision, not a workaround: a filtered model in a restricted collection is a
display convenience and provides no security.

## Collection permissions

| Group | Its entity's domain collections | Its `Explorations` | Other entities | `Group` | `Platform` |
|---|---|---|---|---|---|
| `<entity>_analysts` | Curate | Curate | No access | View | View |
| `<entity>_explorers` | View | Curate | No access | No access | No access |
| `<entity>_readers` | View | No access | No access | No access | No access |
| `group_analysts` | View | No access | View | Curate | View |

Two deliberate asymmetries:

- **Explorers curate `Explorations`, and only view the domain collections.** They
  need somewhere to publish work their colleagues can see, without that work
  landing next to certified dashboards. `Explorations` is that place, and it is
  why the collection exists.
- **Readers are cut off from `Explorations` entirely.** It holds 🚧 content and a
  reader has no way to judge it.

Promotion from `explorers` to `analysts` is therefore a real step: it grants SQL
*and* the right to publish into a domain collection, which is the right to put a
star on something.

## The automation key

The metadata sync (ADR 0017) authenticates with a Metabase API key, and that key
**has to sit in `Administrators`**. Do not create a dedicated least-privilege
group for it: the attempt fails for a reason worth knowing rather than
rediscovering.

Metabase has exactly the right permission — *Manage table metadata*, with a
per-table *Granular* mode — but **data model permissions are Pro/Enterprise
only**. On the open-source edition, editing table metadata is admin or nothing.

The near-miss to avoid: granting the automation group *native SQL* on the
database. Data permissions govern **querying**; metadata editing lives in
**Admin**. Native SQL would give the key more power over the data and still no
power at all over metadata — strictly worse on both counts.

So it is contained rather than scoped down:

- An **API key, not a user account** — revocable in one click, tied to no person.
- **In Key Vault**, readable only by the VM's managed identity, reaching the
  container as an environment variable that no image layer holds.
- **Named for its job** (e.g. `dbt-metabase metadata sync`) so that its presence
  in the admin key list is self-explanatory rather than alarming.
- **Used by one asset**, never by a human authenticating by hand.

Stated plainly, because it is the weakest point on this page: an admin key can
read every table and change every permission. Its blast radius is the whole
instance. If a Pro licence is ever bought, moving it to a group with *Manage
table metadata* is a two-minute change and should be done that day.

## Where table metadata comes from

Descriptions, foreign keys, display names and hidden tables are **not** typed
into Metabase. They come from the dbt `.yml` files and are applied by
`dbt-metabase` after publication — see
[ADR 0017](https://github.com/picot-data/data-platform-standards/blob/main/adr/0017-dbt-metadata-to-metabase-via-api.md).

Two consequences for anyone editing:

- **Do not fix a description in the Metabase UI.** Fix it in dbt; the next sync
  applies it. A UI edit will be overwritten and its author will not know why.
- Foreign keys come from the `relationships` tests on a fact's keys. A missing
  implicit join in the query builder is almost always a missing test, not a
  Metabase problem.

## Setting it up, in order

The order matters: every step but the first is undone by skipping it.

1. Remove the Sample Database, and strip `All Users` of data access.
2. Add the serving databases (`gold_dti`, …) with **read-only** connections.
3. Run `dbt-metabase models` so tables arrive documented, joined and with the
   technical ones hidden.
4. Create the collection tree, top level first.
5. Create the groups, and set data permissions before collection permissions —
   a group with no data access cannot leak anything through a collection while
   you are still working.
6. Add people, and check the result by impersonating a viewer rather than by
   re-reading the permission screen.

## Operating rules

- Any question about *who can see what* is answered by reading two screens —
  data permissions and collection permissions — and never by inspecting
  dashboards.
- A dashboard is one intention, and roughly seven cards. Beyond that, split it.
- Business logic never lives in a Metabase question. A `SUM` or a ratio that
  encodes a business definition belongs in a `mart_` model — see
  [Metric definitions](semantic-layer.md).
- A Metabase model that several dashboards depend on is a signal that it should
  become a dbt model. Metabase models are presentation: scope, renaming, joins
  for convenience. They are not stored in Git, not tested, and not visible to
  lineage.
- Onboarding an entity adds two groups, one collection tree and one serving
  database — never a second Metabase instance. See
  [Onboarding a new entity](onboarding-a-new-entity.md).
