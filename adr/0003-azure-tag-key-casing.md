# ADR 0003: Azure tag keys use PascalCase, as a documented exception to snake_case

**Status**: Accepted

**Date**: 2026-07-30

## Context

The group-wide rule (see [Naming conventions](../docs/naming-conventions.md))
is `snake_case` everywhere, no exceptions — tables, columns, files, cloud
resource names. Azure tags are a different kind of object: key/value pairs
attached to resources for cost and governance purposes, and Microsoft's own
tooling has its own convention for them.

## Options considered

1. **Apply `snake_case` to tag keys too**, for internal consistency with every
   other naming rule in the project.
2. **Use `PascalCase` for tag keys**, matching Microsoft's own CAF examples and
   Azure Policy built-in definitions (`CostCenter`, `Environment`), and how the
   Azure portal displays them.

## Decision

Option 2. Tag *keys* use `PascalCase` (`CostCenter`, `Environment`,
`ManagedBy`). Tag *values* stay lowercase and reuse the same codes as the
resource-naming segments (`dti`, `shared`, `prod`), so a tag value and a name
segment are always the same token. The only exceptions are `Owner` (an email
address) and `ExpiresOn` (a date).

## Consequences

- Azure tag keys are case-insensitive for lookup but case-preserving for
  display, so a key written as `cost_center` would silently fail to match an
  Azure Policy definition expecting `CostCenter` — a mismatch that produces
  silent misses, not errors, and is easy to miss in review.
- Anyone applying the general `snake_case` rule to a tag key without reading
  this exception will produce a tag that looks fine in the portal but does
  not participate in policy enforcement or cost grouping as expected.
