# ADR 0023: The catalog is served from the shared BI VM, on the corporate network

**Status**: Accepted

**Date**: 2026-08-18

## Context

[ADR 0021](0021-dbt-docs-not-datahub-as-the-catalog.md) made dbt docs the catalog
and deliberately left hosting undecided, on the grounds that it was "a small change
to make when a second person needs the catalog often enough to be annoyed by
downloading it". That condition was met immediately: the catalog exists to answer
"where does this figure come from" for whoever asks, and an artifact that has to be
downloaded from a workflow run is not consulted by anyone who is not already
reading CI logs. A catalog nobody opens is the failure ADR 0021 was correcting, at
a lower price.

Two constraints decide where it can live, and they point at the same machine.

- **Entity VMs sleep.** [ADR 0018](0018-scheduled-start-stop-for-entity-vms.md)
  starts an entity VM before its pipeline window and deallocates it after, with a
  hard cut-off. Anything served from there is unreachable most of the day, and
  keeping a VM awake to serve a static page would give back the saving that ADR
  0018 and [ADR 0016](0016-central-metabase-not-per-entity.md) were for. A catalog
  is the *second* thing to have almost kept those machines awake; the first was
  DataHub, which is what ADR 0019 moved and ADR 0021 removed.
- **Exactly one machine is always on**: the shared BI VM
  (`vm-picot-shared-bi-weu-01`), which serves people during working hours and is
  never on a schedule.

The mechanisms needed already exist and are not built for this. The entity pipeline
already publishes dbt's artifacts to the `metadata` container at the end of a run —
while the VM is awake, before it is deallocated. The shared VM already runs a
**scheduled pull** from ADLS to rebuild the serving databases, chosen over a push
precisely so that N entities do not need credentials reaching across landing zones.
The catalog rides both.

That leaves how a person reaches it. A dbt docs site is static HTML with no login
of its own, and it lists every table and column name in the SAP extract. Metabase,
sharing the machine, has its own authentication. How business users reach Metabase
in the target was itself never specified, so this decision settles the door for
both rather than inventing a second one.

## Options considered

1. **Serve it from each entity VM** — closest to where it is produced, and
   unreachable whenever that VM is asleep, which is most of the time. Fixing that
   means not deallocating, which discards ADR 0018.
2. **Leave it as a CI artifact** — the status quo from ADR 0021. Free, and read by
   nobody outside CI.
3. **Publish it to GitHub Pages** — a URL with no infrastructure, and public unless
   the organisation is on GitHub Enterprise Cloud (~21 USD/user/month). Rejected on
   both counts in ADR 0021: it would publish the schema, and paying for
   access-controlled hosting of a static file is the kind of spending this platform
   avoids.
4. **Serve it from the shared BI VM, restricted to the corporate network** — one
   always-on machine that already exists in the design, already pulls from ADLS,
   and already hosts the audience.

## Decision

Option 4. The catalog is served by the shared BI VM, next to Metabase, and reached
over the corporate network.

**How the files get there.** The entity's `dbt_artifacts` asset publishes
`manifest.json`, `catalog.json` **and `index.html`** to
`metadata/company_<code>/dbt/`. `index.html` is the site: a self-contained page
that reads the two JSON files. It was not published before because DataHub only
needed the JSON. The shared VM's scheduled refresh pulls that prefix into a served
directory, one per entity, and a single web server exposes them at
`/catalog/<code>/`.

**Publishing from the VM rather than from CI is deliberate, and it gains
something.** The VM's copy is generated after a real build against real data, so
its `catalog.json` carries the real column types that
`dbt docs generate --empty-catalog` cannot know. The division of labour is
therefore: **CI owns the gate** — it fails on a missing description, credential-free,
on every push — and **the VM owns the published site**. Neither duplicates the
other.

**The network is the access boundary, not a password.** The web server is reachable
only from the corporate network and the VPN, enforced by NSG rules scoped to those
address ranges. No authentication is added in front of the static site: a single
shared password is not revocable per person and would be a second secret to
distribute for no gain over an address restriction that also protects Metabase's
login page from the open internet.

Serving the catalog is the **only** service added to that machine. Nothing
entity-specific is installed there, which ADR 0016 already required.

## Consequences

- **The catalog is a URL.** That is the whole point, and it is what makes the
  traceability argument real rather than theoretical: "where does this figure come
  from" is answered by clicking, by whoever asks, without a download and without
  SSH.
- **Entity VMs keep sleeping.** They deposit and shut down. Nothing is served from
  a machine that is not always on, so ADR 0018's saving is untouched and no new
  ingress is opened on an entity VM — their only inbound rule stays SSH.
- **One place shows every entity's catalog.** Each site is per-project, so this
  does not restore cross-entity *lineage* — the loss ADR 0021 accepted stands — but
  it does restore one place to look, which was the other half of it.
- **Real column types come back**, because the published copy is built from a real
  run rather than with `--empty-catalog`.
- **The address range already exists and is reused, not requested.** The entity
  VM's SSH rule is already scoped to the VPN's egress IP as a single `/32`
  (`admin_source_cidr`), so the catalog's rule is the same value on a different
  port rather than a new dependency on IT.
- **That single `/32` is the fragile part of this decision.** It was observed from
  one workstation on one day. Two things follow, and both are cheaper to know now
  than to debug later: **a user whose traffic egresses elsewhere is silently
  blocked**, so "everyone can reach it" has to be verified per user rather than
  assumed; and **if the VPN rotates its exit IP the catalog goes dark along with
  SSH**, turning one stale value into two outages. The fix in both cases is to
  widen `admin_source_cidr` to the real corporate ranges — at which point it should
  stop being one variable serving both SSH and the catalog, because an
  administrative door and a reading door do not deserve the same list.
- **Remote work outside the VPN cannot reach the catalog.** Accepted: the same is
  true of Metabase, and someone off the VPN is not the audience for a question
  about table provenance.
- **The catalog lags the pipeline by up to one refresh interval**, exactly as the
  BI serving copies do. Acceptable for a catalog, where the question is about
  structure and provenance rather than today's figures.
- **The shared VM gains a second reason to be a single point of failure**, now for
  dashboards and the catalog. Neither is on the pipeline's critical path: an outage
  costs visibility for its duration and no data, and Gold keeps being published
  throughout.
- **Nothing can be served until the shared VM exists.** It is still a commented
  block in `shared/main.tf`. Until then the reference entity runs Metabase — and
  now the catalog — on its own VM as the deviation already documented for
  Metabase, reachable over the SSH tunnel. That is a stated deviation, not this
  decision.
- Revisited if the shared VM's audience ever extends past the corporate network
  (an external auditor, a consultant), at which point the question is
  authentication in front of both services and not a second machine.
