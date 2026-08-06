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
| What is the Azure agreement type (EA or MCA)? Determines whether Cost Management tag inheritance is available, and confirms no native hard spending limit exists | Medium | IT Group / Finance |
