# Architecture Decision Records

ADRs capture the *why* behind a decision — context, options considered, and
consequences — kept separate from the reference docs so those stay short,
affirmative rules. An ADR is immutable once accepted: a changed mind produces
a new ADR that supersedes the old one, not an edit to it.

| ADR | Title | Status |
|---|---|---|
| [0001](https://github.com/picot-data/data-platform-standards/blob/main/adr/0001-medallion-dbt-layer-persistence.md) | Persistence strategy per medallion / dbt layer | Accepted |
| [0002](https://github.com/picot-data/data-platform-standards/blob/main/adr/0002-caf-landing-zone-structure.md) | Adopt the CAF Landing Zone structure, one landing zone per entity | Accepted |
| [0003](https://github.com/picot-data/data-platform-standards/blob/main/adr/0003-azure-tag-key-casing.md) | Azure tag keys use PascalCase, as an exception to snake_case | Accepted |
| [0004](https://github.com/picot-data/data-platform-standards/blob/main/adr/0004-tagging-enforced-via-policy.md) | Tags are enforced by Azure Policy, not by discipline | Accepted |
| [0005](https://github.com/picot-data/data-platform-standards/blob/main/adr/0005-budget-alerts-vs-automated-shutdown.md) | Budget alerts everywhere, automated shutdown only on dev/staging | Accepted |
| [0000](https://github.com/picot-data/data-platform-standards/blob/main/adr/0000-template.md) | Template | — |

Open questions that have not yet been decided are tracked as GitHub issues
labelled `open-question`, not as draft ADRs.
