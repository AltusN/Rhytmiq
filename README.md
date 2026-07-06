# Rhytmiq

A FIG-compliant API for managing rhythmic gymnastics meets — districts, clubs, coaches,
gymnasts, groups, meets, meet entries, routines, and routine profiles.

## Tech stack

- [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic v2](https://docs.pydantic.dev/) for the API layer
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/) ORM + [Alembic](https://alembic.sqlalchemy.org/)
  migrations, backed by a dockerized Postgres (via `psycopg` v3)
- [pytest](https://docs.pytest.org/) for tests
- [ruff](https://docs.astral.sh/ruff/) for linting/formatting, wired up via `pre-commit`

## Getting started

```bash
cp .env.example .env   # edit values as needed
docker compose up -d    # starts Postgres + pgAdmin

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic -c alembic.ini upgrade head

uvicorn app.main:app --reload
```

The API is served at `http://127.0.0.1:8000`. Interactive docs are available at
`/docs` (Swagger UI) and `/redoc`.

The root `Makefile` wraps the common workflows: `make dev` (docker compose up + migrate),
`make migration name="..."` (generate a migration), `make test` (migrate the test database +
run pytest), `make seed` (populate demo data across every table), and `make reset` (wipe the
local Postgres volume and start fresh).

## Database migrations

The schema is never auto-created on app startup — Alembic is the only way to build or update
it. After changing a model in `app/models.py`, generate a migration with
`make migration name="add some column"` (or `alembic revision --autogenerate -m "..."`
directly), review the generated file, then apply it via `make dev` or `alembic upgrade head`.

**Caveat:** adding a new value to an existing enum (e.g. a new `Level`) is not detected by
autogenerate — Postgres enum types need a hand-written migration using
`op.execute("ALTER TYPE ... ADD VALUE ...")`.

## Running tests

```bash
cd backend
pytest
```

Tests run against an isolated in-memory SQLite database per test (see `test/conftest.py`) —
they don't touch the Postgres database used by `uvicorn`/`make dev`. Moving the suite onto
Postgres is tracked as follow-up work.

## Linting

```bash
cd backend
ruff check .
ruff format .
```

`pre-commit` is configured (`backend/.pre-commit-config.yaml`) to run `ruff --fix` and
`ruff format` on commit. It isn't in `requirements.txt`; install it separately
(`pip install pre-commit`) then run `pre-commit install` once to enable the hook.

## Project layout

```
backend/
  app/
    main.py          # FastAPI app, router registration
    db.py             # engine/session setup, get_db dependency
    models.py         # SQLAlchemy ORM models
    routers/          # one router per resource
    schemas/          # Pydantic request/response models
  test/
    conftest.py        # shared fixtures + model factory helpers
    test_models/        # ORM model tests
    test_schemas/        # Pydantic schema tests
    test_routers/         # FastAPI endpoint tests (TestClient)
```

## Domain model

| Entity | Notes |
| --- | --- |
| `District` | Top-level region; owns clubs and meets. |
| `Club` | Belongs to a district; owns coaches, gymnasts, and groups. |
| `Coach` | Belongs to a club. |
| `Gymnast` | Optionally belongs to a club and a group (independent gymnasts allowed). If both are provided, the group must belong to the club. |
| `Group` | A named group of gymnasts within a club (e.g. by age/level). |
| `Meet` | Optionally tied to a district (national/open meets have `district_id = null`). |
| `MeetEntry` | A gymnast's or group's entry into a meet — exactly one of `gymnast_id`/`group_id` is set. |
| `Routine` | One row per apparatus per meet entry. |
| `RoutineProfile` | A gymnast's or group's music/choreography for an apparatus at a level — exactly one of `gymnast_id`/`group_id` is set, unique per (owner, apparatus, level). Resolved live by `Routine.music_url`, not snapshotted per meet. |

## API

Every resource router follows the same REST shape: `POST /`, `GET /`, `GET /{id}`,
`PATCH /{id}`, `DELETE /{id}`.

| Resource | Prefix | Notes |
| --- | --- | --- |
| Districts | `/districts` | |
| Clubs | `/clubs` | |
| Coaches | `/coaches` | |
| Gymnasts | `/gymnasts` | Filter list by `?club_id=` |
| Groups | `/groups` | Filter list by `?club_id=`; create requires a valid `club_id` |
| Meets | `/meets` | Filter list by `?district_id=`, `?status=`. Status transitions are forward-only, enforced server-side. Deleting an `in_progress` or `completed` meet is rejected (`409`). |
| Meet entries | `/meet-entries` | Filter list by `?meet_id=`, `?gymnast_id=`, `?group_id=`. Exactly one of `gymnast_id`/`group_id` required on create; not updatable after creation. |
| Routines | `/routines` | Filter list by `?entry_id=`. One row per apparatus per entry; `entry_id`/`apparatus` not updatable after creation. |
| Routine profiles | `/routine-profiles` | Filter list by `?gymnast_id=`, `?group_id=`, `?apparatus=`, `?level=`. Exactly one of `gymnast_id`/`group_id` required on create; only `music_url`/`choreography_notes` are updatable after creation. |

Deleting a `Meet` or `Gymnast` cascades to their `MeetEntry`/`Routine` rows (unless the meet is
`in_progress` or `completed`, in which case delete is rejected outright). Deleting a
`Club`/`Group`/`District` that still has dependents (gymnasts, coaches, groups, clubs)
is rejected (`409`) via `RESTRICT` foreign keys.
