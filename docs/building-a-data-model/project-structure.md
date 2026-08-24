# dbt project structure

[Data layers](data-layers.md) says which layer a model belongs to. This page
says how to organise the inside of a layer, and why the answer differs from one
layer to the next.

## Folders are not decoration

Two facts make the layout a technical decision rather than a matter of taste.

**Folders are the configuration unit.** `dbt_project.yml` applies settings by
folder path, so moving a model between folders changes its materialization, its
schema, its tags and its metadata:

```yaml
models:
  my_project:
    staging:
      +materialized: table
      +meta:
        publish_container: silver
    marts:
      +meta:
        publish_container: gold
```

They are also a selection unit: `dbt build --select path:models/staging/sap`.

**Folders do not create a namespace.** A model name must be unique across the
whole project. `staging/sap/order.sql` and `staging/ebiz/order.sql` cannot
coexist. This is exactly why the naming convention puts the source in the file
name — `stg_sap__order` — so the name stays unambiguous whether the project is
flat or foldered.

## How to split each layer

The splitting criterion changes with the layer, and the reason is that staging
is the only layer that speaks the source system's language. Everything below it
speaks the business's.

| Layer | Split by | Example |
|---|---|---|
| `staging/` | **source system** | `staging/sap/`, `staging/ebiz/` |
| `intermediate/` | business domain | `intermediate/production/` |
| `dimensions/`, `facts/` | flat, unless the star schema becomes large | — |
| `marts/` | business domain, or consuming department | `marts/sales/`, `marts/production/` |

```
models/
  staging/
    sap/
      _sap__sources.yml
      _sap__models.yml
      stg_sap__customer.sql
      stg_sap__production_order.sql
    ebiz/
      _ebiz__sources.yml
      _ebiz__models.yml
      stg_ebiz__order.sql
  intermediate/
  dimensions/
  facts/
  marts/
    sales/
    production/
```

The leading underscore on the YAML files sorts them to the top of the folder.

## When to split

Not before it earns its keep. Three models in a folder need no subdivision;
fifty do. The practical thresholds:

- **staging** — split at the **second source system**, not before. A second
  business *domain* is not a reason: several domains extracted from one ERP are
  still one source, and stay in one folder.
- **marts** — split at the **second business domain**.

What actually forces the split at scale is prosaic: **merge conflicts.** A
single YAML file edited by everyone produces a conflict on every pull request.
Some teams go as far as one YAML file per model for that reason, at the cost of
losing the overview.

## Where the source declarations go

`_<source>__sources.yml` lives in `models/staging/`, next to the models that
read it. Two reasons, one hard and one soft.

**dbt only reads YAML under `model-paths`.** A `sources.yml` placed anywhere
else — at the repository root, in a `sources/` directory — is silently ignored.
It is not a style choice.

**Staging is the only layer allowed to call `source()`.** An `int_` or `mart_`
model reading a source directly bypasses the staging contract: the renaming, the
casting, the filter on the latest extract. Since the declarations are used in
exactly one place, they are documented in that place — and "where does this
column come from?" is answerable without leaving the folder.

Sources are not models: dbt never builds them, it only knows they exist and
where to read them. They are the roots of the lineage graph. The folder says
where dbt looks, not what kind of object it is.

## File naming

| File | Pattern | Contents |
|---|---|---|
| Source declarations | `_<source>__sources.yml` | the source and its tables |
| Model documentation | `_<source>__models.yml` in staging, `_<layer>__models.yml` elsewhere | descriptions and tests |
| Unit tests | `_<source>__unit_tests.yml` | unit test definitions |
| Model | `<prefix>_<name>.sql` | see [naming conventions](../naming-conventions.md) |

## Related

- [Data layers](data-layers.md) — which layer a model belongs to
- [Naming conventions](../naming-conventions.md) — how to name the model itself
- [Testing](testing.md), [Writing descriptions](writing-descriptions.md) — what
  goes in the YAML files above
