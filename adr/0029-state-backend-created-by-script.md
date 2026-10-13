# ADR 0029: The Terraform state backend is created by a script, not by Terraform

**Status**: Accepted — implements the remote-state item of ADR 0025 trigger A

**Date**: 2026-10-13

## Context

Terraform records what it manages in a **state** file. In the POC that file is
local, on one laptop, and holds secrets in clear
([ADR 0025](0025-identity-only-access-and-private-networking.md), trigger A,
requires moving it to a remote backend with locking and versioning).

A remote backend on Azure is a storage account. It has to exist *before* the
first `terraform init` of any root module, since that is where their state will
live. Whatever creates it therefore cannot store its own state there: a
chicken-and-egg problem every Terraform installation has to solve once.

## Options considered

1. **A dedicated Terraform root module** creates the account and keeps its own
   state as a local file. Everything stays "in Terraform", but one state file
   keeps living on a laptop, or is migrated into the account it describes after
   the fact — a second procedure to get right.
2. **A Terraform root module that migrates its own state** into the account once
   created (`terraform init -migrate-state`). No local file afterwards, but the
   resource that holds every state is then managed by a state stored inside
   itself: a mistaken `destroy` on that root deletes the state of the whole
   platform, including its own.
3. **An idempotent `az` CLI script**, committed and documented, run by hand once.
   No state anywhere for this resource. Terraform cannot detect drift on it.

## Decision

Option 3. The backend is created by an idempotent script in
`terraform-azure-data-platform/bootstrap/`, documented in that folder's README,
and run by the platform owner. Nothing else in the platform is created this way.

## What the script creates

- Resource group `rg-picot-shared-tfstate-frc` in `sub-picot-shared-prod`,
  separate from `rg-picot-shared-data-frc` so that no Terraform root module ever
  owns the group holding the states.
- Storage account `stpicottfstate`: plain blob storage, **no** hierarchical
  namespace, so that blob versioning is available (it is not on ADLS Gen2, see
  [ADR 0026](0026-soft-delete-not-versioning-for-the-lake.md)); ZRS
  ([ADR 0028](0028-france-central-and-zone-redundant-lake.md)); account keys
  disabled; blob versioning and soft delete on; a `CanNotDelete` lock.
- One container, `tfstate`, holding one blob per root module (`shared.tfstate`,
  `entity-dti.tfstate`, …). Terraform's `azurerm` backend locks a state through
  a lease on its blob, so two concurrent applies cannot corrupt it.
- The mandatory tags, with `ManagedBy = manual`.

## Consequences

- **No state file left on a laptop**, for any resource of the platform.
- **The backend is the one sanctioned `ManagedBy = manual` resource group.** The
  Resource Graph query listing drift from the IaC baseline returns it; that
  result is expected, and is the only one that is.
- **Terraform cannot see drift on the backend.** The script is idempotent, so
  re-running it reapplies the intended settings; the lock prevents the one
  change that matters, its deletion.
- **Rebuilding from nothing** is: run the script, then `terraform init` each
  root module. The procedure lives next to the script, not in this ADR, so it is
  updated with the code it describes.
- Access to the states is a data-plane role (`Storage Blob Data Contributor`) on
  the account, granted to whoever runs `terraform apply`. A state can still hold
  secrets, so this role is granted as narrowly as the Key Vault's.
