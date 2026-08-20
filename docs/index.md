# Picot Data Platform — Standards

This site is the single source of truth for how the Picot group's data
platform is built and named, across every entity. Rules live here. The
reasoning behind each rule lives in the [Architecture Decision
Records](adr-index.md). Open questions live as GitHub issues, not in these
pages.

## Where to start

| You are | Start with |
|---|---|
| New to the project entirely | [Platform overview](platform-overview.md), then [Onboarding a data engineer](onboarding-a-data-engineer.md) |
| Writing a dbt model | [Data layers](data-layers.md), then [Naming conventions](naming-conventions.md) and [dbt project structure](project-structure.md) |
| Finishing a dbt model | [Writing descriptions](writing-descriptions.md) and [Testing](testing.md) — a model without either is not finished |
| Adding or changing a metric | [Metric definitions](metric-definitions.md) |
| Building questions and dashboards in Metabase | [Onboarding a data analyst](onboarding-a-data-analyst.md) |
| Administering Metabase, or granting someone access | [BI and access](bi-and-access.md) |
| Provisioning Azure resources | [Azure landing zones](azure-landing-zones.md) |
| Onboarding a new group entity | [Onboarding a new entity](onboarding-a-new-entity.md) |
| Setting up a new repository | [Repositories and delivery](repositories-and-delivery.md) |
| Looking up a term | [Glossary](glossary.md) |

## Scope

This repository holds **group-wide** rules and decisions: naming, tagging,
landing zone structure, data layering conventions, the semantic layer
approach, and delivery conventions (git, CI/CD). It contains no entity-specific
code or data. Each entity repository (e.g. `poc-data-platform-dti`, and future
production repositories) implements these rules and links back here rather
than duplicating them.
