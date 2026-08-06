# ADR 0004: Tags are enforced by Azure Policy, not by discipline

**Status**: Accepted

**Date**: 2026-07-30

## Context

A tagging convention (see [Naming conventions](../docs/naming-conventions.md)
and [Azure landing zones](../docs/azure-landing-zones.md)) only has value if
resources actually carry the tags. Three concrete problems motivated this:
a shared storage account paid once but consumed by every entity, with no way
to reallocate its cost without tags; resources that nobody remembers creating,
with nothing in the resource *name* indicating whether they are still needed;
and SAP business data (confidential) sitting in the same storage account as
public open-data sources, with layer names (bronze/silver/gold) describing
refinement, not sensitivity.

Azure does not inherit tags from a resource group to its child resources by
default — creating a resource in a tagged resource group produces an
untagged resource unless something enforces it.

## Options considered

1. **Rely on discipline** — document the mandatory tags and expect every
   resource creation (manual or Terraform) to include them. Zero setup cost,
   but drifts within a quarter, and by the time it's noticed, retro-tagging
   and reconstructing months of unattributed spend is expensive.
2. **Enforce via Azure Policy at management-group scope** — an `inherit`
   policy that auto-fills a tag from the resource group if absent, followed by
   a `deny` policy that blocks resource creation if a mandatory tag is still
   missing. Assigned once at `mg-picot-landingzones`, it covers every current
   and future subscription and entity automatically.

## Decision

Option 2, with the `inherit` policies assigned **before** the `deny` policies.
Sequencing matters: assigning `deny` first would block legitimate deployments
that the `inherit` policy would have fixed automatically, and the first
reflex to that friction is usually to disable the policy — which is how tag
governance dies in practice.

## Consequences

- No resource can be created without its mandatory tags once both policies
  are active — this is a hard gate, not a reminder.
- The policies require `Resource Policy Contributor` at the
  `mg-picot-landingzones` scope to assign. Whether the data platform Owner
  holds that role is an open question, not assumed by this decision.
- Existing resources created before the policy was assigned need a one-off
  remediation task (`modify` policy effect) to be retro-tagged; this is not
  automatic for resources that already exist at policy assignment time.
