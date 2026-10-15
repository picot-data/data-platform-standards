# ADR 0030: The deployment identity trusts the `main` branch, not a GitHub Environment

**Status**: Accepted — amends the approval-gate item of ADR 0012

**Date**: 2026-10-13

## Context

[ADR 0012](0012-oidc-run-command-deployment.md) binds the Azure federated
credential to a GitHub Environment
(`repo:picot-data/<entity-repo>:environment:production`), the environment
carrying required reviewers, so that a run which has not been approved cannot
obtain an Azure token.

The `picot-data` organisation is on GitHub Free, and every entity repository is
private. GitHub's documentation is explicit about what that combination offers:

- **Required reviewers and wait timers** on a private repository are not
  available on Free, Pro or Team.
- **Environment secrets** on a private repository need Pro, Team or Enterprise.
- **Deployment branch restrictions** on a private repository need Pro or Team.

So on this plan an Environment is a label with no protection at all. Worse, the
binding then protects less than it appears to: any workflow on **any branch**
that declares `environment: production` receives the subject claim and
therefore an Azure token. ADR 0012 recorded the missing reviewers as a
deviation; it did not notice the missing branch restriction. The platform owner
also hit failures creating Environments on these repositories in practice.

## Options considered

1. **Keep the Environment binding** and record the deviation. Any branch can
   deploy; the configuration suggests a gate that does not exist.
2. **Bind the credential to the `main` branch**
   (`repo:picot-data/<entity-repo>:ref:refs/heads/main`). Only a workflow running
   on `main` can obtain a token. Works on every GitHub plan, needs no Environment.
3. **Upgrade the organisation's plan.** Team brings deployment branch
   restrictions and branch protection on private repositories, still not
   required reviewers. A recurring cost for one operator today.
4. **Make the repositories public** to unlock the features. Rejected: entity
   repositories carry subscription ids and network allow-lists.

## Decision

Option 2. Each entity's federated credential trusts
`repo:picot-data/<entity-repo>:ref:refs/heads/main` and nothing else.

> **Amendment, 2026-10-15.** The picot-data repositories present GitHub's
> immutable subject, with numeric ids next to the names:
> `repo:picot-data@<org id>/<entity-repo>@<repo id>:ref:refs/heads/main`. The
> name-only form above was refused (`AADSTS700213`) on the first deployment.
> The binding is unchanged in substance — `main` of one repository — and
> `modules/deployer` (v5.1.0) reads the ids from GitHub. A side benefit: a
> repository deleted and recreated under the same name is not trusted. Deployment
workflows run on `main` only and declare no Environment. Values the deployment
needs (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` — identifiers,
not secrets) are repository variables, which every plan supports.

## Consequences

- **Whoever can push to `main` can deploy.** That is the gate now, and on Free it
  is not enforced by branch protection either. Acceptable while the platform has
  a single operator; the condition that ends it is a second person with write
  access to an entity repository.
- **No human approval step exists**, as before — but it is no longer implied by
  a configuration that looks like one.
- **Everything stays in Terraform.** The app registration, its federated
  credential (`azuread` provider) and the repository variables (`github`
  provider) are created by the entity's `apply`, so onboarding an entity still
  writes no HCL and clicks nothing.
- **Revisited** when a second person gets write access to an entity repository,
  or when the organisation changes plan: on Team, branch protection on `main`
  closes the first consequence without touching this binding; on Enterprise,
  reviewers become possible and the Environment binding of ADR 0012 can return.
