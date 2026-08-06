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

Every Level 1 tool runs on a single Azure VM per entity: ingestion scripts,
Dagster, dbt Core, and DuckDB. Not one VM per tool, not one VM shared across
entities — see
[ADR 0006](https://github.com/picot-data/data-platform-standards/blob/main/adr/0006-single-vm-for-level-1.md).

| Component | Role | Runs as |
|---|---|---|
| Python scripts | Extraction from SAP and other sources | On-demand, invoked by Dagster |
| Dagster OSS (webserver + daemon) | Orchestration | The only continuous service among these four |
| dbt Core | Transformation | CLI, invoked by Dagster |
| DuckDB | Query engine | Embedded — a file, not a server; activated on demand by dbt or a script |

Ingestion is done with in-house Python scripts rather than Airbyte OSS — see
[ADR 0007](https://github.com/picot-data/data-platform-standards/blob/main/adr/0007-python-scripts-not-airbyte.md).

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

## Semantic layer — dbt MetricFlow

Each business metric (e.g. revenue) is defined once, centrally, in
MetricFlow, rather than recomputed differently in every mart or dashboard —
see [Semantic layer](semantic-layer.md).

## Orchestration — Dagster OSS

Dagster schedules and monitors the ingestion and dbt assets. It is the only
component among the four in the compute table above that runs as a
continuous service rather than on demand.

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

Two patterns are in scope for connecting the on-premise SAP system to Azure:
an Azure Data Factory + self-hosted integration runtime bridge (tried first),
or a flat-file export already in production use elsewhere in the group
(the fallback if the ADF bridge proves disproportionate for a POC). Falling
back to the file-export pattern is a documented architecture decision, not a
failure to reach the first option.
