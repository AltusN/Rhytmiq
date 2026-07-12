"""
Tests for the PenaltyRecord model, including:
- Creation with required fields, rejection when required fields are missing
- ck_penalty_record_amount_positive and ck_penalty_record_amount_increments (0.05 steps)
- No uniqueness constraint: the same judge_role can recur multiple times on one routine
- Routine delete cascades to PenaltyRecord; Judge delete is RESTRICTed while records exist
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import PenaltyJudgeRole, PenaltyRecord, Routine
from test.conftest import (
    make_gymnast,
    make_judge,
    make_meet,
    make_meet_entry,
    make_penalty_record,
    make_routine,
)


def test_penalty_record_create_with_required_fields(db_session):
    penalty_record = make_penalty_record(db_session)

    db_session.commit()

    fetched = db_session.query(PenaltyRecord).first()
    assert fetched is not None
    assert fetched.routine_id == penalty_record.routine_id
    assert fetched.judge_id == penalty_record.judge_id
    assert fetched.judge_role == PenaltyJudgeRole.responsible_judge
    assert fetched.description == "test penalty"
    assert fetched.amount == Decimal("0.30")


def test_penalty_record_create_without_required_fields(db_session):
    penalty_record = PenaltyRecord(
        routine_id=None,
        judge_id=None,
        judge_role=None,
        description=None,
        amount=None,
    )
    db_session.add(penalty_record)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_penalty_record_amount_not_positive_rejected(db_session):
    meet_entry = make_meet_entry(
        db_session, meet=make_meet(db_session), gymnast=make_gymnast(db_session)
    )
    routine = make_routine(db_session, meet_entry=meet_entry)
    judge = make_judge(db_session)
    penalty_record = PenaltyRecord(
        routine_id=routine.id,
        judge_id=judge.id,
        judge_role=PenaltyJudgeRole.line_judge,
        description="boundary touch",
        amount=Decimal("0"),  # Invalid: must be > 0
    )
    db_session.add(penalty_record)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_penalty_record_amount_negative_rejected(db_session):
    meet_entry = make_meet_entry(
        db_session, meet=make_meet(db_session), gymnast=make_gymnast(db_session)
    )
    routine = make_routine(db_session, meet_entry=meet_entry)
    judge = make_judge(db_session)
    penalty_record = PenaltyRecord(
        routine_id=routine.id,
        judge_id=judge.id,
        judge_role=PenaltyJudgeRole.line_judge,
        description="boundary touch",
        amount=Decimal("-0.30"),
    )
    db_session.add(penalty_record)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_penalty_record_amount_not_multiple_of_0_05_rejected(db_session):
    meet_entry = make_meet_entry(
        db_session, meet=make_meet(db_session), gymnast=make_gymnast(db_session)
    )
    routine = make_routine(db_session, meet_entry=meet_entry)
    judge = make_judge(db_session)
    penalty_record = PenaltyRecord(
        routine_id=routine.id,
        judge_id=judge.id,
        judge_role=PenaltyJudgeRole.time_judge,
        description="0.5 seconds over",
        amount=Decimal("0.33"),
    )
    db_session.add(penalty_record)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_penalty_record_same_routine_judge_role_recurs_allowed(db_session):
    # No uniqueness constraint -- two separate boundary touches by the Line judge on the
    # same routine, assessed by the same judge, must both be recordable.
    meet_entry = make_meet_entry(
        db_session, meet=make_meet(db_session), gymnast=make_gymnast(db_session)
    )
    routine = make_routine(db_session, meet_entry=meet_entry)
    judge = make_judge(db_session)

    record1 = PenaltyRecord(
        routine_id=routine.id,
        judge_id=judge.id,
        judge_role=PenaltyJudgeRole.line_judge,
        description="first boundary touch",
        amount=Decimal("0.30"),
    )
    record2 = PenaltyRecord(
        routine_id=routine.id,
        judge_id=judge.id,
        judge_role=PenaltyJudgeRole.line_judge,
        description="second boundary touch",
        amount=Decimal("0.30"),
    )
    db_session.add_all([record1, record2])
    db_session.commit()

    fetched = (
        db_session.query(PenaltyRecord)
        .filter_by(routine_id=routine.id, judge_id=judge.id, judge_role=PenaltyJudgeRole.line_judge)
        .all()
    )
    assert len(fetched) == 2


def test_delete_routine_cascades_to_penalty_records(db_session):
    routine = make_routine(db_session)
    penalty_record = make_penalty_record(db_session, routine=routine)
    db_session.commit()

    db_session.delete(routine)
    db_session.commit()

    assert db_session.query(Routine).filter_by(id=routine.id).first() is None
    assert db_session.query(PenaltyRecord).filter_by(id=penalty_record.id).first() is None


def test_delete_judge_with_penalty_records_not_allowed(db_session):
    judge = make_judge(db_session)
    make_penalty_record(db_session, judge=judge)
    db_session.commit()

    db_session.delete(judge)

    with pytest.raises(IntegrityError):
        db_session.commit()
