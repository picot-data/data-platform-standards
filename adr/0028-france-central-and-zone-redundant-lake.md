# ADR 0028: France Central as the platform region, and a zone-redundant lake

**Status**: Accepted — replaces the region choice (West Europe, `weu`) of the
naming table, and amends the lake row of ADR 0025's out-of-scope list

**Date**: 2026-10-13

## Context

Every resource of the POC was created in West Europe, region code `weu`. That
region was never argued for: it was the default of the first `terraform apply`,
and the naming table recorded what existed.

On 2026-10-13 the six landing-zone subscriptions (`sub-picot-dti-*`,
`sub-picot-shared-*`) were delivered empty, and the production rollout rebuilds
everything in them from Terraform. Nothing is yet created in the target
subscriptions, so this is the last moment a region change costs nothing but a
variable.

The lake was also created with locally-redundant storage (LRS): three copies in
a single datacenter. That was never decided either.

Azure offers four redundancy levels for a storage account:

| Level | Copies | Survives |
|---|---|---|
| LRS | 3, in one datacenter | a disk or rack failure |
| ZRS | 3, one in each of the region's three availability zones (separate datacenters) | the loss of a datacenter |
| GRS | LRS, plus an asynchronous copy in the paired region | the loss of the whole region |
| GZRS | ZRS, plus an asynchronous copy in the paired region | both |

France Central has three availability zones. Its paired region is France South,
so even a geo-redundant copy would stay in France.

## Options considered

1. **Stay in West Europe** (Netherlands). No documentation change, and usually
   slightly cheaper. Data leaves France.
2. **Move to France Central**, region code `frc` (the Cloud Adoption Framework
   abbreviation, already used elsewhere in the tenant). Keeps the group's SAP
   data in France. Every service of the platform is offered there: virtual
   machines, ADLS Gen2, Key Vault, Container Registry, Data Factory, Database for
   PostgreSQL.

And, for the lake:

1. **LRS** — cheapest; a datacenter incident can make the lake unavailable, or
   in the worst case lose it.
2. **ZRS** — survives the loss of a datacenter, which is the failure that
   realistically happens.
3. **GZRS** — also survives the loss of the whole region, at a markedly higher
   price than ZRS (storage plus geo-replication traffic — to price on the Azure
   calculator, not assumed).

## Decision

The platform runs in **France Central**, region code **`frc`**, for every
resource of every scope. The shared lake uses **ZRS**.

## Consequences

- **Every name carrying a region segment changes**: `rg-picot-dti-data-frc`,
  `vm-picot-dti-data-frc-01`, `kv-picot-dti-frc-01`, `crpicotdtidatafrc01`, and so
  on. `stpicotdata` carries no region segment and keeps its name. A side effect
  worth having: the new names do not collide with the POC's resources, so only
  `stpicotdata` has to be destroyed before its replacement is created.
- **GZRS is not chosen, and the reason is written down so its absence reads as a
  decision.** Losing France Central entirely is rare, and it would stop the
  entity VMs and the BI machine too: a second copy of the data keeps the data,
  not the platform. Bronze can be re-extracted from SAP and Silver and Gold
  rebuilt by dbt. Revisit if the business requires the data to survive the loss
  of a region, or if SAP starts archiving history that Bronze then holds alone.
- **Replication is not a backup.** A deletion or an overwrite is replicated to
  every copy at once. Recoverability stays with soft delete and the delete lock
  ([ADR 0026](0026-soft-delete-not-versioning-for-the-lake.md)).
- **Prices differ from West Europe**, usually slightly higher. Budget amounts
  are costed against France Central prices on the Azure calculator, not against
  the POC's observed bill.
- **The self-hosted integration runtime is unaffected by the region**: it is an
  agent on a machine outside Azure, re-registered against the new factory at the
  rebuild in any case.
- The redundancy level of a storage account can be changed later without
  recreating it (LRS to ZRS through a conversion, ZRS to GZRS directly), so this
  decision is not a one-way door. The region is: moving a resource between
  regions means recreating it.
