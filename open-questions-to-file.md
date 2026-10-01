# Open questions to file as GitHub issues

Staging list extracted while migrating `naming_convention.md`. These are
questions, not decisions — they don't belong in the reference docs. File each
of these as a GitHub issue (label `open-question`) in this repo, then delete
its entry here. Not linked from `mkdocs.yml` nav on purpose — this file is a
worklist, not documentation.

| Question | Criticality | Stakeholder |
|---|---|---|
| Should `dim_customer`/`dim_product` carry history via a dbt snapshot on staging (e.g. "what was this customer called when the order was placed")? | Medium | CDG (business-rules session) |
| `_loaded_at` is currently set with `current_timestamp` — should it instead reflect the ingestion timestamp derivable from the Bronze date partition? | Medium | Owner, once Bronze is wired |
| Which mechanism writes Parquet to ADLS cleanly under the VM's managed identity — DuckDB's `azure` extension, or an `fsspec`/`abfs` filesystem? | Medium | Owner, at ADLS wiring time |
| Which `CostCenter` code carries the data project — does the IA/LLM workstream share it or need its own? | High — blocks the tag `deny` policy and budget amounts | Finance Dirickx |
| Does IT already have an Azure tagging convention for its own subscriptions? | High — two tag conventions in one tenant breaks group-level cost reporting | IT D / IT Group |
| Who owns `mg-picot-platform`, and does IT plan to put anything there that concerns the data platform (notably a VPN/ExpressRoute to SAP)? | High | IT Group |
| Does the Owner have `Resource Policy Contributor` on `mg-picot-landingzones`? | Medium — without it, tag governance is undeployable | IT Group / tenant admin |
| Budget amounts per subscription and the annual envelope — needs a costing exercise against actual SKUs (D4s_v3, ADLS volumes, Key Vault), not an estimate | High — needed for the CODIR budget ask | Owner + Finance |
| Does the shared storage cost get re-invoiced to entities, or carried by a pivot entity? | Medium — political as much as technical | Finance / Direction |
| Every entity VNet takes `modules/entity`'s default `10.0.0.0/16`, so all entities overlap. Which address plan — one non-overlapping range per entity, compatible with the corporate ranges — before any peering, VPN or private endpoint? | High — must be fixed before a second entity is applied, since a VNet's range cannot change under a running VM without rebuilding its network | Group IT / Owner |
| Postgres for Metabase (ADR 0027): a container on the BI VM, or Azure Database for PostgreSQL? Needs a costed comparison and a backup plan for the application database either way | Medium — needed before the BI VM is built | Owner |
| Group consolidation: should a group Gold layer exist in production, and where does it run? Leaning towards a group dbt project in the shared scope that reads each entity's published Gold read-only, applies intercompany eliminations and currency conversion, and publishes under `gold/company_group/` — never a table written by each entity VM. Not before three preconditions: a second entity actually modelled, conformed models (ADR 0024 phase 2), and a consolidation definition written by the CDG | High once the CDG asks for a consolidated group figure; until then the group view is juxtaposition | CDG / Owner |
| Publication completeness marker: each entity's publication writes `_published.json` (run id, business date, timestamp) last, after every Gold file. Consumers — the BI refresh now, a group build later — read only an entity whose marker is complete; a group build runs only when all entities published the same business date, otherwise it keeps the last valid result and alerts. Without it, an interrupted publication leaves a mix of old and new Gold files that the refresh reads as if whole | Medium — the BI refresh is exposed today; a group build cannot exist without it | Owner |
| What is the Azure agreement type (EA or MCA)? Determines whether Cost Management tag inheritance is available, and confirms no native hard spending limit exists | Medium | IT Group / Finance |
