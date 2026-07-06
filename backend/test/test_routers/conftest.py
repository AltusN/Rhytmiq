"""
Shared fixtures for router tests.

The key pattern here is dependency_overrides: we replace FastAPI's real
get_db (which opens a Postgres connection) with a function that yields the
test's own db_session -- inherited from test/conftest.py, an outer transaction
rolled back at the end of the test -- so every router test runs in complete
isolation with no leftover data, without needing a separate fixture here.

We import `app` directly so the router tests exercise the full request/response
pipeline — middleware, serialisation, status codes — not just the handler logic.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
