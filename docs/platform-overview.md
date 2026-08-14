# Platform overview

This page describes the Level 1 architecture: everything needed to prove the
pipeline end to end, on a single VM per entity, at POC scale.

## The end-to-end flow

<div class="dp-diagram-wrap" markdown="0">
--8<-- "docs/assets/diagrams/platform-overview.svg"
</div>

Every box above is a decision, not an assumption — hover it for detail, click
to jump to the reasoning behind that tool choice.

## Compute — one VM per entity

Every Level 1 tool that needs a machine runs on a single Azure VM per entity:
Dagster, dbt Core, DuckDB, and the non-SAP ingestion scripts. Not one VM per
tool, not one VM shared across entities — see
[ADR 0006](https://github.com/picot-data/data-platform-standards/blob/main/adr/0006-single-vm-for-level-1.md).
Metabase and DataHub are Level 1 tools too, and also run on that same VM —
see [Governance — DataHub](#governance-datahub) and
[Consumption — Metabase](#consumption-metabase) below — but they sit outside
the table because they're consumption/governance layers on top of the core
ingestion-to-transformation pipeline, not part of it.

The one component in the table that is **not** on the VM is Azure Data
Factory: a managed Azure service with its own scheduling and monitoring,
whose self-hosted integration runtime runs on a machine with network access
to the on-premise SAP system — see
[Extraction — SAP to cloud](#extraction-sap-to-cloud).

| Component | Role | Runs as |
|---|---|---|
| Azure Data Factory + self-hosted IR | Extraction from SAP (primary) | Managed Azure service — not on the VM; schedules itself |
| Python scripts | Extraction from non-SAP sources | On the VM — on demand, invoked by Dagster |
| Dagster OSS (webserver + daemon) | Orchestration | On the VM — the only VM tool here that runs continuously rather than on demand |
| dbt Core | Transformation | On the VM — CLI, invoked by Dagster |
| DuckDB | Query engine | On the VM — embedded; a file, not a server, activated on demand by dbt or a script |

SAP ingestion runs through Azure Data Factory rather than a hand-written
script — see
[ADR 0010](https://github.com/picot-data/data-platform-standards/blob/main/adr/0010-adf-not-python-scripts-for-sap.md).
Non-SAP sources still use in-house Python scripts rather than Airbyte OSS —
see [ADR 0007](https://github.com/picot-data/data-platform-standards/blob/main/adr/0007-python-scripts-not-airbyte.md).

## Storage — medallion on ADLS

A single ADLS Gen2 storage account for the whole group (`stpicotdata`), with
one container per medallion layer (`bronze`, `silver`, `gold`, `metadata`),
entity isolation handled by folder prefix rather than by separate accounts.
Every layer is stored as Parquet — see
[ADR 0009](https://github.com/picot-data/data-platform-standards/blob/main/adr/0009-plain-parquet-not-iceberg.md).
The full naming and persistence rules live in
[Naming conventions](naming-conventions.md#cloud-storage-naming-adls) and
[Data layers](data-layers.md).

## Transformation — dbt Core + DuckDB

dbt models the data as a star schema (dimensions and facts), not just ad hoc
marts — see [Data layers](data-layers.md) for the layer-by-layer breakdown and
why the medallion architecture and the dbt model layers are two different,
easily conflated axes.

## Metric definitions — dbt marts

Each business metric (e.g. revenue) is defined once, in a `mart_` model, rather
than recomputed differently in every dashboard — see
[Metric definitions](semantic-layer.md).

This was dbt MetricFlow's job until
[ADR 0015](https://github.com/picot-data/data-platform-standards/blob/main/adr/0015-metrics-in-marts-not-metricflow.md):
MetricFlow only binds consumers that query *through* it, and in dbt Core it is
reachable from a CLI, not from Metabase — so a metric defined there was
invisible in the one place it had to be visible.

## Orchestration — Dagster OSS

Dagster schedules and monitors the dbt assets and the non-SAP ingestion
scripts. SAP extraction is scheduled by Azure Data Factory itself, not by
Dagster — see [Extraction — SAP to cloud](#extraction-sap-to-cloud). Among
the VM tools in the compute table above, Dagster is the only one that runs
as a continuous service rather than on demand.

## Governance — DataHub

DataHub ingests dbt's `manifest.json`/`catalog.json` (produced by
`dbt docs generate`) to build a searchable catalog, a lineage graph from
Bronze to Gold, and a business glossary. It is the heaviest component in the
Level 1 stack — it runs as several Docker containers (backend, search index,
metadata database), unlike the CLI-based tools above — and is installed only
after Dagster and dbt are stable, so that installation problems can be
isolated to one component at a time.

## Consumption — Metabase

Metabase (open-source, self-hosted) queries the Gold layer through DuckDB —
see
[ADR 0008](https://github.com/picot-data/data-platform-standards/blob/main/adr/0008-metabase-not-power-bi.md)
for why Power BI is not the BI tool here.

## Extraction — SAP to cloud

Azure Data Factory with a self-hosted integration runtime is the primary
mechanism for connecting the on-premise SAP system to Azure — automated,
scheduled and monitored, rather than hand-written and hand-scheduled. The
fallback is reusing the ABAP extraction script already in production use
elsewhere in the group, which exports SAP data as flat files — used if the
ADF bridge proves disproportionate for a POC. Falling back to the
ABAP-script pattern is a documented architecture decision, not a failure to
reach the first option — see
[ADR 0010](https://github.com/picot-data/data-platform-standards/blob/main/adr/0010-adf-not-python-scripts-for-sap.md).
