# Architecture Decision Records

ADRs capture the *why* behind a decision — context, options considered, and
consequences — kept separate from the reference docs so those stay short,
affirmative rules. An ADR is immutable once accepted: a changed mind produces
a new ADR that supersedes the old one, not an edit to it.

| ADR | Title | Status |
|---|---|---|
| [0001](https://github.com/picot-data/data-platform-standards/blob/main/adr/0001-medallion-dbt-layer-persistence.md) | Persistence strategy per medallion / dbt layer | Partially superseded by 0013 |
| [0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md) | Adopt the CAF Landing Zone structure, one landing zone per entity | Accepted |
| [0003](https://github.com/picot-data/data-platform-standards/blob/main/adr/0003-azure-tag-key-casing.md) | Azure tag keys use PascalCase, as an exception to snake_case | Accepted |
| [0004](https://github.com/picot-data/data-platform-standards/blob/main/adr/0004-tagging-enforced-via-policy.md) | Tags are enforced by Azure Policy, not by discipline | Accepted |
| [0005](https://github.com/picot-data/data-platform-standards/blob/main/adr/0005-budget-alerts-vs-automated-shutdown.md) | Budget alerts everywhere, automated shutdown only on dev/staging | Accepted |
| [0006](https://github.com/picot-data/data-platform-standards/blob/main/adr/0006-single-vm-for-level-1.md) | A single VM for all Level 1 tools, per entity | Partially superseded by 0016 and 0019 |
| [0007](https://github.com/picot-data/data-platform-standards/blob/main/adr/0007-python-scripts-not-airbyte.md) | In-house Python ingestion scripts, not Airbyte OSS | Partially superseded by 0010 |
| [0008](https://github.com/picot-data/data-platform-standards/blob/main/adr/0008-metabase-not-power-bi.md) | Metabase, not Power BI, as the BI tool | Accepted |
| [0009](https://github.com/picot-data/data-platform-standards/blob/main/adr/0009-plain-parquet-not-iceberg.md) | Plain Parquet at Level 1, not Iceberg or Delta | Accepted |
| [0010](https://github.com/picot-data/data-platform-standards/blob/main/adr/0010-adf-not-python-scripts-for-sap.md) | Azure Data Factory for SAP ingestion, not Python scripts | Accepted |
| [0011](https://github.com/picot-data/data-platform-standards/blob/main/adr/0011-shared-terraform-module-and-entity-template.md) | A shared Terraform module and a template repo, not a copied entity repo | Accepted |
| [0012](https://github.com/picot-data/data-platform-standards/blob/main/adr/0012-oidc-run-command-deployment.md) | Deploy via OIDC, a shared container registry and Azure Run Command, not a self-hosted runner | Accepted |
| [0013](https://github.com/picot-data/data-platform-standards/blob/main/adr/0013-local-duckdb-with-publication-step.md) | dbt materializes locally; a publication step writes Silver and Gold | Accepted |
| [0014](https://github.com/picot-data/data-platform-standards/blob/main/adr/0014-duckdb-scale-ceiling.md) | When a single DuckDB node stops being the right engine | Accepted |
| [0015](https://github.com/picot-data/data-platform-standards/blob/main/adr/0015-metrics-in-marts-not-metricflow.md) | Metric definitions live in dbt marts, not in MetricFlow | Accepted |
| [0016](https://github.com/picot-data/data-platform-standards/blob/main/adr/0016-central-metabase-not-per-entity.md) | One central Metabase for the group, not one per entity | Accepted |
| [0017](https://github.com/picot-data/data-platform-standards/blob/main/adr/0017-dbt-metadata-to-metabase-via-api.md) | dbt documentation reaches Metabase through its API, not through the database | Accepted |
| [0018](https://github.com/picot-data/data-platform-standards/blob/main/adr/0018-scheduled-start-stop-for-entity-vms.md) | Entity VMs are started and stopped on a schedule, with a hard cut-off | Accepted |
| [0019](https://github.com/picot-data/data-platform-standards/blob/main/adr/0019-datahub-joins-the-shared-vm.md) | DataHub joins Metabase on the shared VM, on one machine rather than two | Accepted |
| [0020](https://github.com/picot-data/data-platform-standards/blob/main/adr/0020-shared-scope-as-a-root-module.md) | The group-scoped resources live in a root module, not in a module and not in an entity | Accepted |
| [0000](https://github.com/picot-data/data-platform-standards/blob/main/adr/0000-template.md) | Template | — |

Open questions that have not yet been decided are tracked as GitHub issues
labelled `open-question`, not as draft ADRs.
