"""
Test suite for the penalty record router.
- Post /penalty-records
-- Test creating a penalty record with valid data
-- Test creating a penalty record with invalid routine_id
-- Test creating a penalty record with invalid judge_id
-- Test creating a penalty record with same routine_id/judge_id/judge_role recurring
   (allowed -- no uniqueness constraint, unlike JudgeScore)
-- Test reject adding a PenaltyRecord to a completed meet (409)
- Get /penalty-records
-- Test listing all penalty records
-- Test filtering penalty records by routine_id
-- Test filtering penalty records by judge_id
-- Test filtering penalty records by judge_role
- Get /penalty-records/{penalty_record_id}
-- Test retrieving a penalty record by ID
-- Test retrieving a penalty record with invalid ID
- Patch /penalty-records/{penalty_record_id}
-- Test updating a penalty record with valid data
-- Test updating a penalty record with invalid ID
-- Test updating a penalty record on a completed meet (409)
- Delete /penalty-records/{penalty_record_id}
-- Test deleting a penalty record on a completed meet (409)
-- Test deleting a penalty record by ID
-- Test deleting a penalty record with invalid ID
- Drift guard between Routine.penalty and its PenaltyRecords
-- PATCH /routines/{id} penalty succeeds with zero records (already covered by
   test_routine_router.py's existing test_update_routine_penalty -- not repeated here)
-- PATCH /routines/{id} penalty is rejected (409) once >=1 PenaltyRecord exists
-- POST/PATCH/DELETE a PenaltyRecord each correctly resync Routine.penalty
"""

from decimal import Decimal

from app.models import Apparatus, MeetStatus, PenaltyJudgeRole
from test.conftest import (
    make_club,
    make_district,
    make_gymnast,
    make_judge,
    make_meet,
    make_meet_entry,
    make_routine,
)


def _make_judge_routine(db_session):
    """
    Helper function that creates a judge and a routine, plus exposes the routine's
    meet_entry so callers can build a second routine for the same gymnast on a
    different apparatus. Returns a (routine, judge, meet_entry) tuple. Mirrors
    test_judge_score_router.py's helper of the same name.
    """
    district = make_district(db_session)
    club = make_club(db_session, district=district)
    gymnast = make_gymnast(db_session, club=club)
    meet = make_meet(db_session, district=district)
    meet_entry = make_meet_entry(db_session, meet=meet, gymnast=gymnast)
    routine = make_routine(db_session, meet_entry=meet_entry)
    judge = make_judge(db_session)

    return routine, judge, meet_entry


##-- Post --##
def test_create_penalty_record(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response = client.post("/penalty-records/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["routine_id"] == payload["routine_id"]
    assert data["judge_id"] == payload["judge_id"]
    assert data["judge_role"] == payload["judge_role"]
    assert data["description"] == payload["description"]
    assert Decimal(data["amount"]) == Decimal(str(payload["amount"]))


def test_create_penalty_record_invalid_routine(client, db_session):
    _, judge, _ = _make_judge_routine(db_session)

    payload = {
        "routine_id": 9999,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response = client.post("/penalty-records/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "Routine with id" in data["detail"]


def test_create_penalty_record_invalid_judge(client, db_session):
    routine, _, _ = _make_judge_routine(db_session)

    payload = {
        "routine_id": routine.id,
        "judge_id": 9999,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response = client.post("/penalty-records/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "Judge with id" in data["detail"]


def test_create_penalty_record_same_routine_judge_role_recurs_allowed(client, db_session):
    # No uniqueness constraint -- two separate boundary touches by the same judge on
    # the same routine must both succeed, unlike JudgeScore's one-per-panel rule.
    routine, judge, _ = _make_judge_routine(db_session)

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "first boundary touch",
        "amount": 0.30,
    }
    response1 = client.post("/penalty-records/", json=payload)
    assert response1.status_code == 201

    payload["description"] = "second boundary touch"
    response2 = client.post("/penalty-records/", json=payload)
    assert response2.status_code == 201


def test_create_penalty_record_rejected_on_completed_meet(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    routine.entry.meet.status = MeetStatus.completed
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response = client.post("/penalty-records/", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert f"Meet {routine.entry.meet.id} is completed" in data["detail"]


##-- Get --##
def test_get_empty_penalty_records(client):
    response = client.get("/penalty-records/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_penalty_records(client, db_session):
    routine, judge, meet_entry = _make_judge_routine(db_session)
    db_session.commit()
    routine_2 = make_routine(db_session, meet_entry=meet_entry, apparatus=Apparatus.ball)

    payload_1 = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    payload_2 = {
        "routine_id": routine_2.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.time_judge,
        "description": "1 second over",
        "amount": 0.05,
    }
    client.post("/penalty-records/", json=payload_1)
    client.post("/penalty-records/", json=payload_2)

    response = client.get("/penalty-records/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_penalty_records_by_routine(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    client.post("/penalty-records/", json=payload)

    response = client.get(f"/penalty-records/?routine_id={routine.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert all(record["routine_id"] == routine.id for record in data)


def test_get_penalty_records_by_judge(client, db_session):
    _, judge, meet_entry = _make_judge_routine(db_session)
    db_session.commit()
    routine_2 = make_routine(db_session, meet_entry=meet_entry, apparatus=Apparatus.ball)

    payload = {
        "routine_id": routine_2.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.responsible_judge,
        "description": "attire violation",
        "amount": 0.30,
    }
    client.post("/penalty-records/", json=payload)

    response = client.get(f"/penalty-records/?judge_id={judge.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert all(record["judge_id"] == judge.id for record in data)


def test_get_penalty_records_by_judge_role(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.time_judge,
        "description": "1 second over",
        "amount": 0.05,
    }
    client.post("/penalty-records/", json=payload)

    response = client.get(f"/penalty-records/?judge_role={PenaltyJudgeRole.time_judge}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert all(record["judge_role"] == PenaltyJudgeRole.time_judge for record in data)


def test_get_penalty_record_by_id(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response_create = client.post("/penalty-records/", json=payload)
    assert response_create.status_code == 201
    penalty_record_id = response_create.json()["id"]

    response_get = client.get(f"/penalty-records/{penalty_record_id}")
    assert response_get.status_code == 200
    assert response_get.json()["id"] == penalty_record_id


def test_get_penalty_record_invalid_id(client):
    response = client.get("/penalty-records/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


##-- Patch --##
def test_update_penalty_record_success(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response_create = client.post("/penalty-records/", json=payload)
    assert response_create.status_code == 201
    penalty_record_id = response_create.json()["id"]

    response_update = client.patch(f"/penalty-records/{penalty_record_id}", json={"amount": 0.50})
    assert response_update.status_code == 200
    data = response_update.json()
    assert Decimal(data["amount"]) == Decimal("0.5")
    # routine_id/judge_id are identity fields -- not touched by the update
    assert data["routine_id"] == routine.id
    assert data["judge_id"] == judge.id


def test_update_penalty_record_invalid_id(client):
    response = client.patch("/penalty-records/9999", json={"amount": 0.50})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_update_penalty_record_rejected_on_completed_meet(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    # Create the record while the meet is still open -- the guard would reject
    # this same POST once the meet is completed, so completion has to happen
    # after setup, not before.
    response_create = client.post("/penalty-records/", json=payload)
    assert response_create.status_code == 201
    penalty_record_id = response_create.json()["id"]

    routine.entry.meet.status = MeetStatus.completed
    db_session.commit()

    response_update = client.patch(f"/penalty-records/{penalty_record_id}", json={"amount": 0.50})
    assert response_update.status_code == 409
    data = response_update.json()
    assert f"Meet {routine.entry.meet.id} is completed" in data["detail"]


##-- Delete --##
def test_delete_penalty_record(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    response_create = client.post("/penalty-records/", json=payload)
    assert response_create.status_code == 201
    penalty_record_id = response_create.json()["id"]

    response_delete = client.delete(f"/penalty-records/{penalty_record_id}")
    assert response_delete.status_code == 204

    response_get = client.get(f"/penalty-records/{penalty_record_id}")
    assert response_get.status_code == 404


def test_delete_penalty_record_invalid_id(client):
    response = client.delete("/penalty-records/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


##-- Drift guard between Routine.penalty and its PenaltyRecords --##
def test_create_penalty_record_resyncs_routine_penalty(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()
    assert Decimal(client.get(f"/routines/{routine.id}").json()["penalty"]) == Decimal("0")

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    client.post("/penalty-records/", json=payload)

    response = client.get(f"/routines/{routine.id}")
    assert Decimal(response.json()["penalty"]) == Decimal("0.30")


def test_multiple_penalty_records_sum_into_routine_penalty(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    client.post(
        "/penalty-records/",
        json={
            "routine_id": routine.id,
            "judge_id": judge.id,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        },
    )
    client.post(
        "/penalty-records/",
        json={
            "routine_id": routine.id,
            "judge_id": judge.id,
            "judge_role": PenaltyJudgeRole.time_judge,
            "description": "1 second over",
            "amount": 0.05,
        },
    )

    response = client.get(f"/routines/{routine.id}")
    assert Decimal(response.json()["penalty"]) == Decimal("0.35")


def test_update_penalty_record_resyncs_routine_penalty(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    response_create = client.post(
        "/penalty-records/",
        json={
            "routine_id": routine.id,
            "judge_id": judge.id,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        },
    )
    penalty_record_id = response_create.json()["id"]

    client.patch(f"/penalty-records/{penalty_record_id}", json={"amount": 0.50})

    response = client.get(f"/routines/{routine.id}")
    assert Decimal(response.json()["penalty"]) == Decimal("0.50")


def test_delete_penalty_record_resyncs_routine_penalty(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    response_create = client.post(
        "/penalty-records/",
        json={
            "routine_id": routine.id,
            "judge_id": judge.id,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        },
    )
    penalty_record_id = response_create.json()["id"]

    client.delete(f"/penalty-records/{penalty_record_id}")

    response = client.get(f"/routines/{routine.id}")
    assert Decimal(response.json()["penalty"]) == Decimal("0")


def test_update_routine_penalty_directly_rejected_once_records_exist(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    client.post(
        "/penalty-records/",
        json={
            "routine_id": routine.id,
            "judge_id": judge.id,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        },
    )

    response = client.patch(f"/routines/{routine.id}", json={"penalty": "0.95"})
    assert response.status_code == 409
    assert "itemized penalty records" in response.json()["detail"]

    # And the routine's penalty is unchanged by the rejected attempt.
    get_response = client.get(f"/routines/{routine.id}")
    assert Decimal(get_response.json()["penalty"]) == Decimal("0.30")


def test_delete_penalty_record_rejected_on_completed_meet(client, db_session):
    routine, judge, _ = _make_judge_routine(db_session)
    db_session.commit()

    payload = {
        "routine_id": routine.id,
        "judge_id": judge.id,
        "judge_role": PenaltyJudgeRole.line_judge,
        "description": "boundary touch",
        "amount": 0.30,
    }
    # Create the record while the meet is still open -- the guard would reject
    # this same POST once the meet is completed, so completion has to happen
    # after setup, not before.
    response_create = client.post("/penalty-records/", json=payload)
    assert response_create.status_code == 201
    penalty_record_id = response_create.json()["id"]

    routine.entry.meet.status = MeetStatus.completed
    db_session.commit()

    response_delete = client.delete(f"/penalty-records/{penalty_record_id}")
    assert response_delete.status_code == 409
    data = response_delete.json()
    assert f"Meet {routine.entry.meet.id} is completed" in data["detail"]
