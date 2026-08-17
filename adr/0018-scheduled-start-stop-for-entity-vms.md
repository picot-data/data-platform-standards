# ADR 0018: Entity VMs are started and stopped on a schedule, with a hard cut-off

**Status**: Accepted

**Date**: 2026-08-17

## Context

An entity VM used to have to be awake all day, because it served the
dashboards. [ADR 0016](0016-central-metabase-not-per-entity.md) moved Metabase
off it and [ADR 0019](0019-datahub-joins-the-shared-vm.md) moved DataHub, which
leaves Dagster, dbt Core, DuckDB and the ingestion scripts — a batch workload
with a window of minutes, not hours. Nothing interactive depends on the machine
between runs.

The
[hard-limits table](../docs/azure-landing-zones.md#hard-limits) already
anticipated this and recorded the blocker: auto-shutdown was to be enabled
"only once the pipeline window is well defined — never if it could overlap a
Dagster run". Both halves of that condition are now satisfiable.

A deallocated VM costs nothing in compute. The managed disk is still billed, at
a small fraction of the compute price, so the saving is close to the ratio of
awake hours to the day.

This is a different question from
[ADR 0005](0005-budget-alerts-vs-automated-shutdown.md), which decided that a
*budget breach* never stops a `prod` resource automatically. That decision
stands: this is a planned, predictable schedule, not an emergency brake, and it
never fires because of a cost threshold.

## Options considered

1. **Leave the VMs running** — simplest, and pays 24/7 for a machine used for
   minutes a day.
2. **Fixed start and fixed stop** — a cron to start, a cron to stop. Predictable,
   and either too tight (a long run is killed mid-flight) or too loose (hours
   paid for nothing). The stop time has to be guessed from the longest run
   anyone remembers.
3. **Fixed start, stop when the work is done, plus a fixed cut-off** — the
   pipeline deallocates its own VM once it has finished, and an Azure
   auto-shutdown schedule catches every case where it did not.

## Decision

Option 3, in three parts.

**Start: a scheduled GitHub Actions workflow running `az vm start`.** It reuses
the OIDC federation already in place for deployment
([ADR 0012](0012-oidc-run-command-deployment.md)) — no new Azure resource, no
new stored credential, and one less thing than an Automation Account. GitHub's
cron is best-effort and can be delayed under load, so the start is scheduled
**an hour before** the pipeline, not five minutes before.

**Stop: the pipeline deallocates its own VM as its last step**, after a
successful run. This is better than a stop schedule for two reasons, and the
second matters more than the first:

- It cannot cut a run short, because it *is* the end of the run. No guessing
  how long the longest run takes.
- **A failed run leaves the VM up.** That is the desired behaviour, not a
  side effect: the machine that failed is still there to be inspected, with its
  logs and its half-written DuckDB file, instead of having to be restarted into
  a different state.

This requires the VM's managed identity to hold deallocation rights on its own
VM resource — a role scoped to that single resource, granted in the shared
Terraform module.

**Cut-off: an Azure auto-shutdown schedule at a fixed hour, every day.** This
is what makes the previous paragraph safe. Leaving a failed run's VM up is only
useful for as long as someone might look at it; a failure on the first day of a
holiday would otherwise bill three weeks of idle compute. The cut-off is late
enough that no successful run could still be in progress, and it is
unconditional — it does not know or care whether the run failed.

## Consequences

- **Compute cost becomes roughly proportional to the pipeline window** rather
  than to the calendar. This is the largest single cost reduction available at
  Level 1, and it exists only because the consumption tools moved off the
  machine.
- **An ad hoc run needs the VM started first.** Someone wanting to trigger
  Dagster at 15:00 has to start the VM, and the Dagster UI is unreachable until
  they do. That is the real cost of this decision, and it is acceptable
  precisely because dashboards no longer live there — the people who look at
  data daily are unaffected; the person who occasionally re-runs a pipeline is
  the platform owner.
- **Schedules inside Dagster only fire while the VM is up.** A schedule
  configured outside the window silently never runs. Every Dagster schedule
  must therefore sit inside the awake window, and that constraint has to be
  checked when a schedule is added — it is not enforced by anything.
- **Three mechanisms have to agree on one window.** The start workflow, the
  Dagster schedule and the cut-off are in three different places (GitHub
  Actions, Dagster, Terraform). They are documented together in
  [Azure landing zones](../docs/azure-landing-zones.md#hard-limits) so that a
  change to one prompts a look at the others; nothing prevents them from
  drifting apart.
- **The stop step must not fail the run.** A run whose data work succeeded and
  whose deallocation failed is a successful run with a cost problem, not a
  failed pipeline — otherwise a transient Azure error would show up as a data
  incident. The cut-off is the backstop for exactly that case.
- **The BI VM is not on a schedule.** It serves dashboards and a catalog to
  people during working hours, which is the opposite workload. Applying this
  ADR to it would be a misreading.
- Revisited if the platform gains anything interactive on an entity VM, or if
  runs become frequent enough through the day that the window stops being a
  window.
