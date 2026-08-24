# ADR 0017: dbt documentation reaches Metabase through its API, not through the database

**Status**: Accepted

**Date**: 2026-08-17

## Context

Metabase needs three things that dbt already knows, and that a user would
otherwise re-enter by hand in *Table Metadata*:

- **Foreign keys.** Without them the query builder offers no implicit joins, so
  "sales by customer region" requires hand-written SQL instead of two clicks.
  The star schema's whole self-service promise
  ([Data layers](../docs/building-a-data-model/data-layers.md#why-a-star-schema-not-marts-built-directly-from-staging))
  depends on this one piece of metadata.
- **Table and column descriptions**, which Metabase shows on hover — the only
  place a business user will ever read them.
- **Which columns to hide.** Every Silver and Gold table carries `_source_system`
  and `_loaded_at` (see
  [Naming conventions](../docs/naming-conventions.md#technical-metadata-columns)),
  which are traceability, not analysis, and should not sit in a field picker
  next to `amount_excl_tax`. Technical *tables* need no hiding: the serving
  database exposes only Gold, so `stg_` and `int_` models never reach Metabase
  at all.

The obvious route is to make the database itself carry all three, and let
Metabase's sync pick them up. Two independent facts close that route.

**Gold reaches Metabase as Parquet behind views.**
[ADR 0013](0013-local-duckdb-with-publication-step.md) publishes Gold as one
Parquet file per model, and [ADR 0016](0016-central-metabase-not-per-entity.md)
exposes it through a serving DuckDB holding *views* over those files. Neither
Parquet nor a view carries a constraint or a comment. So even with
`contract: enforced` and `persist_docs` set on every dbt model, the database
Metabase actually opens contains none of it. And Metabase does not infer a
foreign key through a view even when the underlying table has one — that is an
open issue, whose stated workaround is to set the semantic types manually "or
build automation".

**Metabase's comment sync is a one-shot seed, by design.** Metabase reads JDBC
`REMARKS` as a description only while its own field is empty, and never
overwrites a description afterwards. That behaviour exists to protect a user's
manual edits, and it is the right default — but it means a description
corrected in dbt would never reach an already-synced Metabase. For a platform
whose whole claim is that dbt is the source of truth, a channel that ignores
subsequent corrections is not a channel.

So the database route would require changing the publication design, would rely
on a DuckDB driver capability that is unverified, and would still only deliver
one of the three needs.

## Options considered

1. **Materialize the serving copy as tables with dbt contracts and
   `persist_docs`** — makes the metadata a property of the database, readable by
   any future tool. But it discards ADR 0013's "views over fresh Parquet"
   property, depends on the community DuckDB driver exposing constraint metadata
   over JDBC (unverified), hits a known dbt-duckdb failure when re-running
   models that other models reference by foreign key, and still leaves
   descriptions unsolved because of the seed-only sync above.
2. **Configure Table Metadata by hand in Metabase** — zero tooling. It is also
   work redone from scratch every time the container is recreated, drifts from
   dbt the day after it is finished, and grows linearly with every entity added.
3. **Push dbt's metadata into Metabase through its REST API**, driven by
   `manifest.json` — the dbt `.yml` files stay the single source of truth,
   nothing in the data path changes, and all three needs are covered by one
   mechanism.

## Decision

Option 3, using **`dbt-metabase`** rather than a script written for this
platform. Its `models` command reads the dbt manifest and applies to Metabase:
primary and foreign keys (derived from `relationships` tests or dbt
constraints), table and column descriptions, semantic types, `visibility_type`
for hiding technical tables, and display names.

Writing our own client was considered and rejected: this is a solved,
maintained problem, and the API surface involved (`/api/table/:id`,
`/api/field/:id`) is exactly what the tool already wraps.

The foreign keys are derived from **`relationships` tests** on every fact's
keys, not from a Metabase-specific `meta` entry. A `relationships` test is a
data quality check that should exist regardless — it fails the build when a fact
row points at a dimension row that is not there — so the declaration earns its
place twice and there is no BI-only config to keep in step with the model. Where a
key genuinely has no testable parent, `metabase.fk_target_table` remains
available as the explicit exception.

Authentication is a Metabase API key, held in the entity's Key Vault, never in
a repository or a `.env` committed to one.

**The key belongs to `Administrators`, and in the open-source edition there is
no alternative.** Metabase API keys inherit the permissions of the group they
are assigned to and are not superuser by default, so the instinct is to give the
key its own least-privilege group. Metabase does have exactly the permission
that would allow it — *Manage table metadata* — but data model permissions are a
Pro/Enterprise feature. On the open-source edition, editing table metadata is
admin or nothing.

That is accepted rather than worked around, and contained instead:

- The identity is an **API key, not a user account**, so it can be revoked in
  one click without touching a person.
- It lives in Key Vault, readable only by the VM's managed identity, and reaches
  the container as an environment variable that no image layer contains.
- It is used by exactly one asset, and is never a credential anyone
  authenticates with by hand.

What is given up honestly: an admin key can read every table and change every
permission, so it is a genuine privilege escalation compared with the pipeline's
other credentials, and its blast radius is the whole Metabase instance. If the
group ever buys a Pro licence, moving the key to a group with *Manage table
metadata* is a two-minute change and should be done.

The command runs after publication, not as part of the dbt build: it describes
what was published, so running it earlier would document models that may not
have passed their tests.

## Consequences

- **dbt `.yml` files become the source of truth for BI metadata too.** A column
  description written once in a PR shows up on hover in a dashboard. That is the
  same guarantee the platform already makes for the data itself, extended to its
  documentation.
- **Recreating the Metabase container no longer loses the metadata.** It is
  reapplied by re-running one command, which is what makes the BI instance
  reproducible rather than hand-tuned — the "how do we know this isn't
  hand-assembled on a VM" question, answered for the BI layer as well.
- **The Metabase API is not versioned and may change between releases.** Their
  documentation says so explicitly. This is contained rather than solved: the
  Metabase version is pinned in the image, so the API only moves when we move
  it, and a failed metadata sync degrades documentation without breaking a
  single dashboard or query. It is a loud, harmless failure.
- **A new dependency with a single maintainer.** If `dbt-metabase` stops being
  maintained, the fallback is a few hundred lines against two endpoints. The
  exit cost is low, and is the reason this is acceptable at all.
- **Compatibility must be verified before automating.** The tool publishes no
  compatibility matrix against Metabase 63. It is run manually once, against
  the pinned version, before being wired into a schedule.
- **`visibility_type` replaces a manual habit.** Demoting a technical column to
  *details-only* becomes a line of dbt `meta`, reviewed like any other config,
  instead of a checkbox someone remembers to tick on one table and forgets on
  the next.
- **`dbt-metabase exposures` is available and deliberately not adopted yet.** It
  writes Metabase questions and dashboards back into dbt as exposures, which
  would extend lineage from Bronze all the way to the dashboard. Worth doing
  once the forward direction is stable; adopting both at once would make a
  failure ambiguous.
- **dbt contracts remain worth having, for their own reasons.** Dropping option
  1 rejects contracts as a *route to Metabase*, not as a practice. Type
  enforcement at build time is a separate quality question, to be decided on its
  own merits and not as a side effect of a BI need.
- This is revisited if Metabase starts inferring foreign keys through views, or
  starts re-syncing descriptions from the database. Either would make the
  database route viable and this mechanism redundant.

## References

- [Metabase — foreign keys not detected on views (#64899)](https://github.com/metabase/metabase/issues/64899)
- [Metabase — descriptions not re-synced from the database (#38694)](https://github.com/metabase/metabase/issues/38694),
  [(#70029)](https://github.com/metabase/metabase/issues/70029)
- [`dbt-metabase`](https://github.com/gouline/dbt-metabase)
- [Metabase — API keys](https://www.metabase.com/docs/latest/people-and-groups/api-keys)
- [Metabase — data permissions](https://www.metabase.com/docs/latest/permissions/data)
  (*Manage table metadata* is Pro/Enterprise only)
- [dbt-duckdb — foreign key constraints fail on re-run (#425)](https://github.com/duckdb/dbt-duckdb/issues/425)
