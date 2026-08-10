# ADR 0011: A shared Terraform module and a template repo, not a copied entity repo

**Status**: Accepted

**Date**: 2026-08-10

## Context

[Onboarding a new entity](../docs/onboarding-a-new-entity.md) already states
that a new entity reuses the same Terraform module (only a new `.tfvars`
file) and the same mono-repo structure. Neither statement holds unless that
reuse is backed by something other than copy-paste: if the Terraform module
and the mono-repo skeleton physically live inside each entity repo, the
second entity onboarded is a fork of the first, and a fix made for `dti`
never reaches `bg` unless someone remembers to port it by hand — exactly the
drift [ADR 0004](0004-tagging-enforced-via-policy.md) and the standards
site's own no-duplication rule exist to prevent, just moved from governance
docs to infrastructure code.

A decision was needed on where the Terraform module, the mono-repo skeleton,
and the CI pipeline actually live, so that "same module, new `.tfvars`" is
literally true rather than aspirational.

## Options considered

1. **Copy the whole entity repo (`poc-data-platform-dti` or its production
   successor) as the starting point for every new entity.** Zero new
   tooling, but the Terraform module, CI workflow, and folder skeleton fork
   at the moment of copy — a fix to any of them has to be reapplied by hand
   to every entity repo already created.
2. **A shared, versioned Terraform module repository** (own repo, tagged
   releases), consumed by each entity's `infra/terraform/` as a thin root
   module (`source = "git::...?ref=vX.Y.Z"`), plus a **GitHub template
   repository** for the mono-repo skeleton (copied once, no live link
   afterward), plus a **reusable GitHub Actions workflow repository** for the
   CI pipeline (`uses: .../entity-ci.yml@ref`).
3. **A monorepo-of-entities** — one repository containing every entity's
   `ingestion/`, `transformation/`, etc. side by side. Rejected already by
   [Repositories and delivery](../docs/repositories-and-delivery.md#why-one-repo-per-entity-not-one-mega-mono-repo-for-the-whole-group)
   for access-boundary reasons; restated here only because it would also
   solve the duplication problem, at the cost of the isolation ADR 0002
   depends on.

## Decision

Option 2. Three separate repos, each deduplicating one concern, at one Git
provider (GitHub, so `data-platform-standards`, the entity repos, and these
three share the same review/PR/branch-protection surface):

- **`terraform-azure-data-platform`** — the actual infrastructure code, as
  two modules: `modules/entity` (resource group, VM, NSG, Key Vault) and
  `modules/governance` (budgets, action groups, scoped to the resource group
  `modules/entity` creates). Mandatory tags stay a `local.common_tags` block
  in the entity's own root module, as
  [Azure landing zones](../docs/azure-landing-zones.md#tagging-strategy)
  already specifies — folding tags into `modules/governance` too would make
  it depend on `modules/entity`'s resource group while `modules/entity`
  depends on `modules/governance`'s tags, a dependency cycle. Each
  entity's `infra/terraform/` calls both by a pinned tag, plus its own
  `<code>.tfvars` and Terraform backend/state configuration. Bumping the
  `ref` is an explicit, per-entity commit followed by `terraform plan` before
  `apply` — a module fix does not silently change infrastructure that hasn't
  opted in yet.
- **`data-platform-entity-template`** — a GitHub *template repository*
  holding the mono-repo skeleton described in
  [Entity mono-repo structure](../docs/repositories-and-delivery.md#entity-mono-repo-structure)
  (`ingestion/`, `transformation/`, `orchestration/`, `infra/`,
  `docs/runbook.md`, `pyproject.toml`) with `<entity>` placeholders. Used via
  "Use this template"; copied once, not kept in sync afterward — same
  trade-off cookiecutter/Copier-style tools make, without adding a
  templating dependency for two to three entities.
- **`data-platform-workflows`** — the reusable CI workflow
  (`entity-ci.yml`, `on: workflow_call`) implementing
  [Minimal CI/CD](../docs/repositories-and-delivery.md#minimal-cicd). Each
  entity's `ci.yml` is a few lines calling it with `uses:`.

None of these three repos hold entity-specific code or data, so they live
alongside `data-platform-standards`, not inside it — this repo stays
documentation-only, per its own stated scope.

## Consequences

- A module or workflow fix is one change in one repo; each entity adopts it
  on its own schedule by bumping a `ref`, rather than a fix needing to be
  reapplied by hand across every entity repo.
- The mono-repo skeleton itself is **not** kept in sync after creation — a
  structural change to the template (a new top-level folder, say) has to be
  back-ported by hand to entities already onboarded. Acceptable at two to
  three entities; if the group reaches five or more, this decision should be
  revisited in favor of a templating tool that supports update-in-place
  (e.g. Copier).
- [Onboarding a new entity](../docs/onboarding-a-new-entity.md) step 2
  becomes "bump the module `ref` and add a `.tfvars`" rather than "run the
  existing module", and step 5 becomes "use the template repo" rather than
  "create a repo following the structure".
- Terraform module versions can now legitimately differ between entities
  (`dti` on `v1.2.0`, `bg` on `v1.3.0`) — this is a feature, not drift, as
  long as it is visible in each entity's `infra/terraform/` source line, and
  is not left to diverge indefinitely without a reason.
