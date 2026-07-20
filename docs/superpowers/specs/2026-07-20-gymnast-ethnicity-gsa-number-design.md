# Gymnast: ethnicity and GSA number

Add two optional fields to `Gymnast`: `ethnicity` (enum) and `gsa_number` (unique string).

## Motivation

South African federations report demographic breakdowns, and Gymnastics South Africa
issues each registered member a GSA number. Neither is FIG-mandated, so both are
optional and neither participates in gymnast identity.

## Data model

New `StrEnum` in `app/models.py`, alongside the existing enums:

```python
class Ethnicity(StrEnum):
    white = "white"
    black = "black"
    coloured = "coloured"
    indian = "indian"
    prefer_not_to_say = "prefer_not_to_say"
```

`prefer_not_to_say` is a distinct value from NULL: NULL means the question was never
asked or the answer is unknown, `prefer_not_to_say` means the gymnast declined. Both are
representable.

New columns on `Gymnast`:

| column | type | null | notes |
|---|---|---|---|
| `ethnicity` | `Enum(Ethnicity)` (native PG enum) | yes | |
| `gsa_number` | `String(32)` | yes | `UniqueConstraint("gsa_number", name="uq_gymnast_gsa_number")` |

`gsa_number` is unique so the same membership number cannot be captured against two
gymnasts. Postgres treats NULLs as distinct under a unique constraint, so any number of
gymnasts without a GSA number coexist.

`gsa_number` does **not** replace `uq_gymnast_identity` on
`(first_name, last_name, date_of_birth)`. It is an optional external ID that many
gymnasts will not have; identity stays as it is. The `Gymnast` docstring records this.

## Schemas

Both fields are added to `GymnastCreate`, `GymnastUpdate` and `GymnastRead`, all
optional and defaulting to `None`.

Both are updatable after creation — these are correctable data-entry fields, and the
frontend uses one shared form for create and edit that PATCHes dirty fields. A field
rendered in that form but missing from `GymnastUpdate` would produce a silent no-op 200.

`gsa_number` gets a `field_validator` in the style of the existing `strip_whitespace`:
strip, then coerce `""` to `None`. Without this, two gymnasts saved from a form with the
GSA field left blank would both store `""` and collide under the unique constraint.

`ethnicity` needs no validator; Pydantic validates enum membership and rejects unknown
strings with a 422.

## Router

`app/routers/gymnast.py` needs no handler changes. Create and update both build the ORM
instance from `payload.model_dump(...)`, so new schema fields flow through
automatically. The existing `try/except IntegrityError -> rollback + HTTPException(409)`
wrapper turns a duplicate `gsa_number` into a 409 rather than a 500; this is covered by
a test rather than assumed.

## Migration

Generated with `make migration name="add_ethnicity_and_gsa_number_to_gymnasts"`.
Autogenerate handles creating a new enum type — the documented blind spot is adding
values to an *existing* enum, which this is not. The generated file is read before
`alembic upgrade head` runs.

## Tests

Written per module as each module is finished, not batched at the end.

`test/test_models/test_gymnast.py`
- a gymnast persists and reads back each `Ethnicity` value
- both columns accept NULL
- duplicate non-null `gsa_number` raises `IntegrityError`
- two gymnasts with NULL `gsa_number` coexist

`test/test_schemas/test_gymnast.py`
- an unknown ethnicity string is rejected
- whitespace-only `gsa_number` normalises to `None`
- fields omitted from a `GymnastUpdate` payload stay unset under `exclude_unset=True`

`test/test_routers/test_gymnast_router.py`
- create with both fields returns 201 and echoes them in the read model
- PATCH updates each field
- create with a duplicate `gsa_number` returns 409

The 409 case is its own test function. The router-test fixture shares one transaction, so
the router's `db.rollback()` on the 409 path would undo commits made earlier in the same
test.

## Frontend

`make types` regenerates `frontend/src/api/schema.d.ts` after the schema change.

`GymnastForm.tsx` (shared by create and edit) gains:
- `ethnicity` as a `<select>` whose blank option means "not set", listing the five enum
  values with readable labels
- `gsa_number` as a text input
- both added to the Zod schema, `defaultValues`, `GymnastBody` and `buildBody`, following
  the existing `toText` / `""`-means-null convention

`GymnastsPage.tsx` gains a GSA number column. Ethnicity is deliberately **not** shown in
the roster table — it is demographic data with no operational use on a screen visible
around a meet venue. It remains editable in the form.

Vitest coverage in `frontend/test/` mirrors the new fields.

## Out of scope

- Reporting or aggregation over ethnicity
- Validating GSA number format (the real format is not confirmed; free text for now)
- Backfilling existing gymnast rows
