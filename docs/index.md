# Picot Data Platform — Standards

This site is the single source of truth for how the Picot group's data
platform is built and named, across every entity. Rules live here. The
reasoning behind each rule lives in the [Architecture Decision
Records](adr-index.md). Open questions live as GitHub issues, not in these
pages.

## Where to start

| You are | Start with |
|---|---|
| New here, and you will write dbt models | [Platform overview](platform-overview.md), then [Onboarding a data engineer](onboardings/onboarding-a-data-engineer.md) |
| New here, and you will build dashboards | [Onboarding a data analyst](onboardings/onboarding-a-data-analyst.md) |
| Deciding where a model goes, and what to call it | [Data layers](building-a-data-model/data-layers.md), then [dbt project structure](building-a-data-model/project-structure.md) and [Naming conventions](naming-conventions.md) |
| Finishing a model before opening a pull request | [Writing descriptions](building-a-data-model/writing-descriptions.md) and [Testing](building-a-data-model/testing.md) — a model without either is not finished |
| Defining a business figure, or deciding it belongs in dbt rather than Metabase | [Metric definitions](building-a-data-model/metric-definitions.md) |
| Administering Metabase, or granting someone access | [BI and access](bi-and-access.md) |
| Provisioning Azure resources | [Azure landing zones](azure-landing-zones.md) |
| Bringing a new group entity onto the platform | [Onboarding a new entity](onboardings/onboarding-a-new-entity.md) |
| Setting up a repository, or changing what CI and deployment do | [Repositories and delivery](repositories-and-delivery.md) |
| Looking up a term | [Glossary](glossary.md) |
| Asking why a rule is what it is | [Architecture Decision Records](adr-index.md) |

## Scope

This repository holds **group-wide** rules and decisions: naming, tagging,
landing zone structure, data layering conventions, how a business metric is
defined once, and delivery conventions (git, CI/CD). It contains no entity-specific
code or data. Each entity repository (e.g. `poc-data-platform-dti`, and future
production repositories) implements these rules and links back here rather
than duplicating them.
