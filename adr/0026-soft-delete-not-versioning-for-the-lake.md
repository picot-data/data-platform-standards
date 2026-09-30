# ADR 0026: Soft delete and a delete lock protect the lake, not blob versioning

**Status**: Accepted — amends the recoverability item of ADR 0025 trigger A

**Date**: 2026-09-30

## Context

[ADR 0025](0025-identity-only-access-and-private-networking.md) lists, under
trigger A, "blob soft delete and versioning enabled; a `CanNotDelete` lock on
the account". Implementing it showed that half of that item cannot be done.

`stpicotdata` is an ADLS Gen2 account: its hierarchical namespace is what makes
it a data lake rather than plain blob storage. On such an account Microsoft does
not support **blob versioning**, nor the two features built on top of it,
**change feed** and **point-in-time restore**, nor **object replication**. A
Terraform apply requesting versioning fails. The hierarchical namespace cannot be
switched off on an existing account either, so keeping versioning would mean a
new account under a new name — the globally unique name the platform owner chose
to protect.

What ADLS Gen2 does support: **soft delete for blobs and for containers**, and
**immutable storage**.

## Options considered

1. **Recreate the lake without a hierarchical namespace**, to gain versioning.
   Loses directory semantics and the `stpicotdata` name, and reverses the
   storage choice for a feature.
2. **Soft delete for blobs and containers, plus the delete lock.** Recovers any
   deleted file or container during the retention window; the lock stops the
   account itself from being deleted.
3. **Immutable storage (time-based retention) on `bronze`.** The strongest
   guarantee: nothing in Bronze can be deleted or overwritten until its retention
   ends, by anyone. But it also makes a mistaken write permanent, and it needs a
   retention period, which is a business and compliance decision not yet taken.

## Decision

Option 2. Soft delete is enabled for blobs and containers with a 30-day
retention, and a `CanNotDelete` lock is placed on the account. This replaces
"soft delete and versioning" in ADR 0025 trigger A; the rest of that trigger is
unchanged.

## Consequences

- **Deletions are recoverable; overwrites should be treated as not
  recoverable.** Without versioning there is no previous version of a file that
  was rewritten in place. Bronze is append-only, with one dated file per extract,
  which is what makes this acceptable: a Bronze file is written once and never
  rewritten. A pipeline that starts overwriting Bronze breaks this guarantee
  silently.
- **Soft-deleted data is billed as ordinary storage** for the retention window.
  Silver and Gold are rewritten on every run and leave one soft-deleted copy
  each; they are small.
- **The lock is inherited by the account's child resources.** Removing the
  Bronze lifecycle policy, or deleting a container through Terraform, needs the
  lock lifted for that apply. That friction is the point.
- **There is still no second copy of the lake.** A regional outage, or a
  compromised identity that deletes and then waits out the retention window, is
  not covered. Geo-redundancy is out of scope at Level 1 (ADR 0025).
- Revisited when a Bronze retention period is agreed — immutable storage on
  `bronze` becomes the natural next step, since the one missing input is that
  period — or if Microsoft adds versioning for accounts with a hierarchical
  namespace.

## References

- [Blob Storage feature support in Azure storage accounts](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-feature-support-in-storage-accounts)
  — versioning, change feed and point-in-time restore are not supported with a
  hierarchical namespace; soft delete and immutable storage are.
