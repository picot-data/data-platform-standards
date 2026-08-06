# ADR 0005: Budget alerts everywhere, automated shutdown only on dev/staging

**Status**: Accepted

**Date**: 2026-07-30

## Context

Azure Cost Management budgets are a notification mechanism, not a spending
cap: reaching 100% of a budget sends an alert and changes nothing else — the
resources keep running and the bill keeps growing. Actually stopping spend
requires a second layer: Budget → Action Group → an automation runbook that
deallocates the resource. A decision was needed on where that second,
automated layer is worth the cost of building — and where it isn't.

## Options considered

1. **Alerts only, everywhere** — cheapest, but a runaway resource in `dev` or
   `staging` (which are supposed to stay empty at Level 1) is only caught when
   a human reads an email.
2. **Automated shutdown everywhere, including `prod`** — the strongest
   guarantee against overspend, but it trades cost control for availability:
   a budget threshold crossed by legitimate growth would shut down the
   pipeline that feeds the BI tool, with no human in the loop.
3. **Automated shutdown on `dev`/`staging`, alerts only on `prod`** — dev and
   staging are supposed to be empty; if something runs there, stopping it
   costs nothing and catches the single most common cloud cost leak (someone
   spins up a VM "just to test" and forgets it). `prod` is different: a human
   should decide between absorbing a cost overrun and accepting a pipeline
   outage.

## Decision

Option 3. Every scope gets budget alerts, at 50/80/100/110% actual and 100%
forecast. Automated deallocation via Budget → Action Group → runbook is
implemented on `dev` and `staging` subscriptions only.

## Consequences

- A `prod` budget breach never automatically stops the pipeline — it always
  waits for a human decision. This means a genuine cost overrun in production
  requires someone to act on the alert; it will not resolve itself.
- The forecast-100% alert is the one to act on before the money is spent,
  rather than after — it should be treated as the primary signal, not the
  100%-actual alert.
- If the business later decides a `prod` budget breach *should* stop the
  pipeline automatically, that is a new decision (stale dashboards accepted as
  the cheaper failure than overspend) and would need its own ADR rather than a
  silent change to the automation.
