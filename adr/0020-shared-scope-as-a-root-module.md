# ADR 0020: The group-scoped resources live in a root module, not in a module and not in an entity

**Status**: Accepted

**Date**: 2026-08-18

## Context

[ADR 0011](0011-shared-terraform-module-and-entity-template.md) moved the
Terraform code out of the entity repos so that onboarding an entity is "same
module, new `.tfvars`". It answered the question for everything an entity owns.
It did not answer it for what the *group* owns.

There are two such resources. The shared ADLS account (`stpicotdata`) exists
today; the BI machine running Metabase and DataHub
([ADR 0016](0016-central-metabase-not-per-entity.md),
[ADR 0019](0019-datahub-joins-the-shared-vm.md)) does not exist yet but is
decided. Both are singletons by design: the lake is shared so that group-level
reporting can read several entities' Gold in one query, and the BI instance is
shared because a dashboard comparing entities is the platform's reason to exist.

`modules/storage` was extracted into the shared repository, and the
documentation then said it is called "once, by whichever root module owns the
shared subscription". **No such root module existed.** In practice the account is
created by the `dti` entity's Terraform state, inside `rg-picot-poc-dti-weu`,
tagged `Entity=dti`. So the second entity's lake would have been managed by the
first entity's state — the exact coupling extracting the module was meant to
remove, moved from code into state, where it is harder to see.

A second question arrived with it, asked plainly: does a machine that exists in
one copy need to be in Terraform at all?

## Options considered

1. **Leave the shared resources in the first entity's repo.** Nothing to build.
   Entity two's lake is then governed by entity one's state file, and destroying
   or renaming anything in that repo puts the group's only non-rebuildable data
   at risk.
2. **A `modules/shared` or `modules/bi` module**, called by something. Consistent
   with how entity resources are packaged, but a module earns its indirection by
   being instantiated more than once — this one would be a wrapper around a
   single call, with every value passed through twice.
3. **A sixth repository** holding only the shared root module. Clean boundary,
   and a clone, a README and a CI setup for roughly sixty lines of HCL.
4. **A root module `shared/` inside `terraform-azure-data-platform`**, alongside
   the modules it calls.
5. **Create the BI machine by hand in the portal** and describe it in the docs,
   on the grounds that a single machine created once is not worth automating.

## Decision

Option 4: the group-scoped resources live in a **root module**, `shared/`, in
`terraform-azure-data-platform` — plain resources, one `.tfvars`, one state. It
owns the shared lake, and it is where the BI machine is created when it is
created.

Option 5 is rejected: the BI machine goes into Terraform despite being a
singleton. Reuse is not the argument. Four others are:

1. **Tags are enforced by policy** at `mg-picot-landingzones` scope
   ([ADR 0004](0004-tagging-enforced-via-policy.md)). A portal-created machine
   either fails the assignment or gets its tags typed once and never corrected,
   and `ExpiresOn` and `CostCenter` are only worth having if they are true.
2. **It holds the second non-rebuildable thing in the platform.** Metabase's
   application database is the group's dashboards, users and permissions. Its
   disk, its size and its backup have to be described somewhere, and "whoever
   clicked" is not a description.
3. **It needs RBAC.** The refresh reads published Gold from the lake, so the
   machine needs an identity with `Storage Blob Data Reader` — read only, unlike
   an entity VM's Contributor, because a BI host has no business writing to the
   lake. A hand-made role assignment is invisible drift, and a missing one
   surfaces as a 403 that DuckDB reports as a credentials error.
4. **ADR 0018's cut-off is a resource**, not a habit.

The human data-plane grant on the lake moves into this root module as well. It
used to sit in the entity's root module, which meant the second entity onboarded
would silently decide who can read the first entity's data. Entity *VMs* are
unaffected: `modules/entity` still grants its own identity from the account id it
is passed, so onboarding an entity still writes no HCL.

## Consequences

- "Who owns the lake?" has an answer that is a directory, not a convention. A
  second entity can be onboarded without its lake being a tenant of the first
  entity's state.
- The repository's own rule — "module code only, no state, no `.tfvars`" — is
  amended rather than worked around: it exists to keep *entity* values out, and
  group-level values have no entity repo to live in. The exception is stated in
  that repo's README, so the next reader does not have to infer it.
- **Adoption is a state migration, not an apply.** The account exists and is
  managed elsewhere, so it has to be imported here and removed from the entity's
  state — a procedure that is not reversible by re-running Terraform, and is
  therefore documented step by step rather than automated. Nothing breaks while
  there is a single entity, which is why it is deliberately not urgent.
- The BI machine being decided and not created stays visible: the root module
  documents where it lands and what it needs, and the onboarding page marks the
  BI step as a target. This is the one place where "the documentation is ahead of
  the platform" is a stated position rather than an accident.
- Level 2 would revisit option 3. Once the shared scope holds more than a lake
  and a BI host — a hub network, a Log Analytics workspace, a state backend — it
  becomes a landing zone of its own with its own lifecycle, and a repository of
  its own stops being overhead.
