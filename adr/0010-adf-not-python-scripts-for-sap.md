# ADR 0010: Azure Data Factory for SAP ingestion, not Python scripts

**Status**: Accepted

**Date**: 2026-08-10

## Context

ADR 0007 chose in-house Python scripts over Airbyte OSS for Level 1
ingestion, on the grounds that Airbyte's RAM footprint didn't fit the
single-VM budget. That decision didn't settle *how* the SAP extraction
itself should be built — it only ruled out Airbyte. Since then, the group
has confirmed it wants to standardize on Azure-native, automated ingestion
tooling rather than hand-written scripts wherever a managed alternative
exists, and SAP already has a flat-file export path in production use
elsewhere in the group, built on an ABAP extraction script.

## Options considered

1. **Azure Data Factory + self-hosted integration runtime** — a managed,
   scheduled, monitored pipeline bridging on-premise SAP to Azure. Native
   retry, monitoring and scheduling come for free; the ongoing engineering
   cost is pipeline configuration, not custom code.
2. **Reuse the existing ABAP extraction script** — already in production use
   elsewhere in the group for exporting SAP data as flat files. Nothing new
   to build, but ingestion stays tied to SAP-side code this platform team
   doesn't own, and to the file-export cadence that script was designed for.
3. **In-house Python scripts** (ADR 0007's original choice) — lightweight
   and fully controlled, but every source, including SAP, is hand-written
   and hand-maintained code with no built-in scheduling, retry or
   monitoring.

## Decision

Option 1. Azure Data Factory with a self-hosted integration runtime is the
primary mechanism for SAP ingestion. Option 2 — reusing the existing ABAP
extraction script — is the documented fallback if the ADF bridge proves
disproportionate for a POC, matching the pattern already described in
[Platform overview — Extraction, SAP to cloud](../docs/platform-overview.md#extraction-sap-to-cloud).

## Consequences

- Partially supersedes ADR 0007: for **SAP** extraction specifically, ADF
  replaces Python scripts. ADR 0007's reasoning against Airbyte OSS (RAM
  footprint on the shared Level 1 VM) still stands, and Python scripts
  remain the ingestion mechanism for non-SAP sources (APIs and similar),
  where no equivalent managed pipeline or existing script is in place.
- A self-hosted integration runtime becomes new infrastructure to install
  and maintain, on top of the four tools already on the Level 1 VM (ADR
  0006).
- If the ABAP-script fallback is used instead of ADF, SAP ingestion depends
  on code the platform team doesn't own or version — acceptable as a
  documented fallback, not as the default.
- Falling back to option 2 is a deliberate architecture decision, not a
  failure to reach option 1.
