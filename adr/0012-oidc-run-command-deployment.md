# ADR 0012: Deploy via OIDC, a shared container registry and Azure Run Command, not a self-hosted runner

**Status**: Accepted

**Date**: 2026-08-13

## Context

[ADR 0006](0006-single-vm-for-level-1.md) puts everything at Level 1 on one VM
per entity, and the platform now ships as a container image rather than as a
native install on that VM. Something therefore has to move an image from CI
onto the VM and restart the stack, for every entity, without either opening a
port or leaving a durable credential somewhere.

Two constraints shaped the choice:

- The NSG created by `modules/entity` allows SSH from a single admin CIDR and
  nothing else, deliberately. A GitHub-hosted runner has an unpredictable
  egress IP, so it cannot reach the VM directly, and widening the NSG to
  GitHub's published ranges would defeat the rule it exists to enforce.
- [ADR 0011](0011-shared-terraform-module-and-entity-template.md) requires that
  onboarding an entity be "same module, new `.tfvars`". A deployment mechanism
  that needs bespoke per-entity wiring — a machine registered by hand, a token
  minted by hand — silently breaks that promise even if the Terraform part
  holds.

The first implementation in the DTI entity satisfied the first constraint but
not the second: a GitHub Actions **self-hosted runner** installed on the VM
polling GitHub outbound, pulling from **GitHub Container Registry** with a
personal access token stored in the entity's Key Vault. It works, and it opens
no port. But it registers a machine by hand, it stores a long-lived token that
someone has to rotate, and — the decisive point — a self-hosted runner executes
whatever a workflow tells it to, as a user in the `docker` group, which is root
on the host in all but name. Anyone able to push to the deployment branch has
root on the entity's VM and therefore reaches its managed identity, its Key
Vault and its data.

## Options considered

1. **Self-hosted runner on the VM + GHCR + a pull token in Key Vault.** No port
   opened, no Azure credential given to GitHub, registry free of charge. Costs a
   permanent agent with root-equivalent access on the VM, a long-lived token to
   store and rotate per entity, and a machine to register per entity.
2. **GitHub-hosted runner + OIDC federated credential + an Azure Container
   Registry per entity + `az vm run-command invoke`.** No agent on the VM, no
   stored secret anywhere, and both the Azure role assignments and the federated
   credential are Terraform resources, so they come with the entity rather than
   being wired by hand.
3. **SSH from a GitHub-hosted runner.** Requires either widening the NSG to
   GitHub's egress ranges or storing a private key in GitHub. Rejected on both
   counts.
4. **A pull-based agent on the VM** (a timer that polls the registry for a new
   tag and redeploys itself). Removes GitHub's access to Azure entirely, but a
   deployment stops being an auditable, approvable event with a known actor: the
   VM decides when to change, rollback becomes "push an older tag and wait", and
   nothing records who authorised what.

## Decision

Option 2, in four parts:

- **An Azure Container Registry per entity**, `cr<entity naming prefix without
  separators>`, in that entity's own resource group. ACR was chosen over GHCR
  because a VM can pull from it with its own **managed identity** (`AcrPull`),
  which is what removes the stored pull token. It is *per entity* rather than
  shared for two reasons that compound: the image is not shareable anyway — it
  bakes in that entity's dbt project and Dagster definitions — and ACR's AAD
  role assignments apply to the **whole registry**, never to a single image
  repository. Repository-scoped permissions do exist, but only as non-AAD tokens
  on the Premium tier, which a managed identity cannot present. A shared
  registry would therefore let any entity's CI overwrite any other entity's
  images, contradicting the one-landing-zone-per-entity boundary of
  [ADR 0002](0002-caf-landing-zone-structure.md). The name drops separators
  because ACR forbids them, the same way the shared storage account does (see
  [Naming conventions](../docs/naming-conventions.md)).
- **OIDC workload identity federation** for GitHub → Azure. GitHub presents a
  signed token describing the workflow; Entra ID returns a short-lived Azure
  token. No secret exists in GitHub.
- **`az vm run-command invoke`** to carry out the deployment. The command
  travels over the Azure control plane to the VM's guest agent, so no inbound
  port is involved and no agent of GitHub's runs on the VM. The script passed is
  self-contained and receives the image tag as a parameter, so the VM holds no
  copy of the repository and nothing needs to be kept in sync on it.
- **A GitHub Environment named `production`**, carrying required reviewers, as
  the gate on the deploy job — and the federated credential's subject is bound
  to that environment
  (`repo:picot-data/<entity-repo>:environment:production`). A run that has not
  passed the gate cannot obtain an Azure token at all, so the approval is
  enforced by Azure rather than being a GitHub-side courtesy that a workflow
  edit could remove.

The Azure role granted to GitHub is a **custom role limited to
`Microsoft.Compute/virtualMachines/runCommand/action`**, never
`Virtual Machine Contributor` — the latter can delete the VM, and nothing about
deploying requires that.

## Consequences

- No durable secret remains in the deployment path: the GHCR pull token is
  deleted from Key Vault, and nothing replaces it. The only credentials involved
  are minted per run and expire.
- Onboarding an entity gains no manual deployment step. The `AcrPull` assignment
  and the `runCommand` role assignment are produced by `modules/entity` from the
  shared resource ids it is passed, and the federated credential is a Terraform
  resource too. There is no machine to register and no token to mint.
- `run-command` executes as **root** on the VM. This is not less privilege than
  the self-hosted runner had — it is privilege that is granted by a scoped,
  revocable Azure role and recorded in the Azure Activity Log, instead of by a
  permanent agent whose actions are visible only in GitHub.
- GitHub gains a role on the Azure control plane, which it did not have before.
  This is the real cost of the decision, and the reason the role is custom and
  single-action rather than a built-in one.
- ACR is billed, unlike GHCR, and being per entity the cost recurs per entity.
  At Basic tier it is a small fixed monthly amount each. Because the image's
  dependency layers are shared across tags, the included storage covers a
  working set of builds — but Basic has no retention policy (that is a Premium
  feature), so pruning old tags becomes a manual chore rather than a setting as
  they accumulate.
- Deployment logs are returned in the `run-command` response rather than streamed
  live. Debugging a failed deployment is less comfortable than reading a runner's
  console, which is why the deployment script keeps polling the webserver's
  `/server_info` before reporting success — a green deployment must mean the
  platform answered, not merely that containers were created.
- Creating the app registration and the federated credential requires rights on
  the group's Entra ID tenant. Where those rights sit with central IT rather
  than with the platform owner, this becomes a request to make rather than a
  step to run, and it gates nothing else: the registry and the role definitions
  can be applied first.
- This supersedes the informal preference for GHCR recorded while
  containerising the DTI entity. That choice was made before its cost — a
  long-lived token in Key Vault per entity — was visible.
