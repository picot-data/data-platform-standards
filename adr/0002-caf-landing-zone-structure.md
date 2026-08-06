# ADR 0002: Adopt the CAF Landing Zone structure, one landing zone per entity

**Status**: Accepted

**Date**: 2026-07-30

## Context

The group has multiple entities (Dirickx today, others to follow) that each
need their own Azure compute and their own billing/governance boundary, while
sharing a single data lake. A structure was needed for management groups and
subscriptions that supports onboarding a new entity without reorganizing what
already exists.

## Options considered

1. **A single subscription for everything**, resource groups per entity.
   Simplest to set up, but cost and access control cannot be cleanly split per
   entity, and it does not match how Azure billing/governance boundaries are
   designed to work.
2. **Microsoft's Cloud Adoption Framework (CAF) Enterprise-Scale Landing Zone
   pattern**: a root management group, split into `Platform` (transverse
   IT-owned services), `Landing Zones` (the actual workloads), and
   `Decommissioned` (a parking lot for retired subscriptions) — with CAF's
   default `Corp`/`Online` split replaced by one landing zone per entity, since
   that split doesn't map to this group's organization.
3. **One subscription per entity, no landing zone / management group
   hierarchy at all.** Closer to option 1 with subscription-level isolation,
   but no standard place to apply group-wide policy (tag enforcement, budget
   structure) without repeating it per subscription.

## Decision

Option 2. Each entity gets its own landing zone management group
(`mg-picot-lz-<code>`) holding three subscriptions — `dev`, `staging`, `prod`
— following the same template for every entity, plus one shared landing zone
(`mg-picot-lz-shared`) for the group-wide resources (the single ADLS storage
account). Policy and budget scaffolding are assigned once, at the
`mg-picot-landingzones` scope, so they apply automatically to every current
and future landing zone.

## Consequences

- Onboarding a new entity means adding one management group and three
  subscriptions under the existing template, with no changes to the existing
  structure — see [Onboarding a new entity](../docs/onboarding-a-new-entity.md).
- At Level 1, only the `prod` subscription of each landing zone is actually
  populated with resources. `dev` and `staging` exist as governance
  scaffolding (RBAC, budget tripwires, Terraform workspace) but stay empty —
  this is a deliberate separation between the *governance structure* (posed
  now, CAF-compliant) and the *resources actually provisioned* (Level 1,
  minimal). It is not a contradiction with a lean POC, and it means no
  subscription reorganization is needed when a real dev/staging environment
  becomes worth the overhead at Level 2.
- `mg-picot-platform` (connectivity, identity, central management) is created
  as an empty placeholder, owned by group IT, out of data-platform scope.
  Whether IT populates it with resources that concern the data platform (in
  particular, a VPN/ExpressRoute connection to SAP) is an open question, not
  assumed either way by this decision.
