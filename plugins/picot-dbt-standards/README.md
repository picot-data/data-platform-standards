# picot-dbt-standards

A Claude Code plugin that makes this repository's standards enforceable by an
agent. It ships in the same repository as the documents it enforces, so a rule
and the tool that applies it move in the same commit and cannot drift apart.

It does **not** reimplement generic dbt practice — the
[dbt Labs marketplace](https://github.com/dbt-labs/dbt-agent-skills) already
covers how to write a model, run dbt and add a unit test. This plugin covers
only the delta: the rules that are ours.

## Skills

| Skill | What it does | User-invocable |
|---|---|---|
| `reviewing-dbt-yaml-against-standards` | Reports findings on a dbt properties YAML — `unique` on a foreign key, a `dbt_utils` test missing its package prefix, arguments not nested under `arguments:`, a blacklist where a bound was meant, a description restating the column name, naming violations. Never edits. | yes |
| `generating-dbt-test-battery` | Derives the tests a model needs to meet the minimum bar, in our required syntax, applying "test where the guarantee is created" so it does not pile tautologies on downstream layers. | yes |
| `drafting-dbt-descriptions` | Writes the structure, the grain sentence and the mechanical facts — and refuses to invent a business definition, marking it `TODO(definition):` and asking instead. | yes, with a named target |

`drafting-dbt-descriptions` was `user-invocable: false` until 2026-09-11. The
reason was sound — a bare "write my descriptions", fired with no model and no
SQL in context, is exactly the situation in which an agent fabricates — but the
remedy was not. Withholding the command also removed the only way a human could
force the skill to engage when the agent failed to reach for it, and that is the
failure that actually happened: descriptions written straight into a properties
YAML, skill never invoked, with the SQL open in the same session.

The guard now lives inside the skill instead of in its availability. Its first
step is to refuse an invocation that names no model and no file, and to ask
which one — having no target is not a thin brief to work around, it is the
absence of the only evidence a description may be derived from.

## Install

Inside Claude Code:

```
/plugin marketplace add picot-data/data-platform-standards
/plugin install picot-dbt-standards@picot-data-platform-standards
```

The first command registers this GitHub repository as a plugin marketplace;
the second installs the plugin from it. The skills are then available in every
session, and all three as
`/picot-dbt-standards:reviewing-dbt-yaml-against-standards`,
`/picot-dbt-standards:generating-dbt-test-battery` and
`/picot-dbt-standards:drafting-dbt-descriptions` — the last one expecting the
model or properties file to document as its argument.

To pull updates after a change is merged here, update the marketplace first,
then the plugin:

```
/plugin marketplace update picot-data-platform-standards
/plugin update picot-dbt-standards@picot-data-platform-standards
```

## Where the rules come from

Each skill loads a condensed, enforceable checklist from
[`references/`](references/) and links to the published page for the
reasoning:

| Checklist | Source of truth |
|---|---|
| `references/testing-checklist.md` | [`docs/building-a-data-model/testing.md`](../../docs/building-a-data-model/testing.md) |
| `references/naming-checklist.md` | [`docs/naming-conventions.md`](../../docs/naming-conventions.md), [`docs/building-a-data-model/project-structure.md`](../../docs/building-a-data-model/project-structure.md), [`docs/building-a-data-model/data-layers.md`](../../docs/building-a-data-model/data-layers.md) |
| `references/description-checklist.md` | [`docs/building-a-data-model/writing-descriptions.md`](../../docs/building-a-data-model/writing-descriptions.md) |

**The checklists are a second copy of rule text that also lives in `docs/`.**
That is a deliberate trade — a self-contained, token-efficient reference the
agent can load without depending on the repository layout — and it can drift.
Two things keep the copies honest:

1. Every checklist names its source page in its first lines, and the skills
   link the published page for the reasoning, so a reader always knows which
   document wins. **`docs/` is authoritative; the checklist is a projection.**
2. A change to any of the four source pages must update the matching
   checklist in the same pull request. This is the rule to enforce in review,
   and the obvious candidate for a CI check: fail the build when a commit
   touches `docs/building-a-data-model/testing.md`,
   `docs/building-a-data-model/writing-descriptions.md`,
   `docs/naming-conventions.md`, `docs/building-a-data-model/project-structure.md` or
   `docs/building-a-data-model/data-layers.md` without touching
   `plugins/picot-dbt-standards/references/`. That check is not implemented
   yet.
