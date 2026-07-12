"""
Pydantic validation tests for the PenaltyRecordCreate/PenaltyRecordUpdate/
PenaltyRecordRead schemas: amount must be > 0 and a multiple of 0.05, description must
be non-empty, and judge_role is a plain PenaltyJudgeRole enum with no cap-style
model_validator (unlike JudgeScoreCreate's artistry/execution cap).
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import PenaltyJudgeRole
from app.schemas.penalty_record import (
    PenaltyRecordCreate,
    PenaltyRecordRead,
    PenaltyRecordUpdate,
)


class TestPenaltyRecordCreate:
    def test_valid_record(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        }
        record = PenaltyRecordCreate.model_validate(data)
        assert record.routine_id == 1
        assert record.judge_id == 1
        assert record.judge_role == PenaltyJudgeRole.line_judge
        assert record.description == "boundary touch"
        assert record.amount == Decimal("0.3")

    def test_invalid_amount_zero(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0,
        }
        with pytest.raises(ValidationError) as exc_info:
            PenaltyRecordCreate.model_validate(data)
        assert "greater than 0" in str(exc_info.value)

    def test_invalid_amount_negative(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": -0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_invalid_amount_not_multiple_of_0_05(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.33,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_invalid_empty_description(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "",
            "amount": 0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_invalid_judge_role(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": "invalid",
            "description": "boundary touch",
            "amount": 0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_judge_role_accepts_plain_string(self):
        # Real HTTP JSON bodies send judge_role as a string, not an enum member.
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": "time_judge",
            "description": "0.5 seconds over",
            "amount": 0.05,
        }
        record = PenaltyRecordCreate.model_validate(data)
        assert record.judge_role == PenaltyJudgeRole.time_judge

    def test_create_record_missing_routine_id(self):
        data = {
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_missing_judge_id(self):
        data = {
            "routine_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": 0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_missing_judge_role(self):
        data = {"routine_id": 1, "judge_id": 1, "description": "boundary touch", "amount": 0.30}
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_missing_description(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "amount": 0.30,
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)

    def test_create_record_missing_amount(self):
        data = {
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
        }
        with pytest.raises(ValidationError):
            PenaltyRecordCreate.model_validate(data)


class TestPenaltyRecordUpdate:
    def test_valid_update(self):
        data = {"amount": 0.50}
        record_update = PenaltyRecordUpdate.model_validate(data)
        assert record_update.amount == Decimal("0.5")

    def test_invalid_update_amount_zero(self):
        data = {"amount": 0}
        with pytest.raises(ValidationError):
            PenaltyRecordUpdate.model_validate(data)

    def test_invalid_update_amount_negative(self):
        data = {"amount": -0.30}
        with pytest.raises(ValidationError):
            PenaltyRecordUpdate.model_validate(data)

    def test_invalid_update_amount_not_multiple_of_0_05(self):
        data = {"amount": 0.33}
        with pytest.raises(ValidationError):
            PenaltyRecordUpdate.model_validate(data)

    def test_invalid_update_empty_description(self):
        data = {"description": ""}
        with pytest.raises(ValidationError):
            PenaltyRecordUpdate.model_validate(data)

    def test_update_judge_role_is_settable(self):
        # Unlike JudgeScoreUpdate (panel is locked, part of a UniqueConstraint),
        # PenaltyRecordUpdate allows changing judge_role -- there's no uniqueness
        # constraint tying it to identity.
        data = {"judge_role": PenaltyJudgeRole.responsible_judge}
        record_update = PenaltyRecordUpdate.model_validate(data)
        assert record_update.judge_role == PenaltyJudgeRole.responsible_judge

    def test_update_exclude_unset_only_includes_provided_fields(self):
        # The router builds updates via payload.model_dump(exclude_unset=True) --
        # this is the actual contract the PenaltyRecordUpdate router handler depends on.
        record_update = PenaltyRecordUpdate.model_validate({"amount": 0.50})
        assert record_update.model_dump(exclude_unset=True) == {"amount": Decimal("0.5")}


class TestPenaltyRecordRead:
    def test_read_record(self):
        data = {
            "id": 1,
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": Decimal("0.30"),
        }
        record_read = PenaltyRecordRead.model_validate(data)
        assert record_read.id == 1
        assert record_read.routine_id == 1
        assert record_read.judge_id == 1
        assert record_read.judge_role == PenaltyJudgeRole.line_judge
        assert record_read.description == "boundary touch"
        assert record_read.amount == Decimal("0.30")

    def test_read_record_invalid_judge_role(self):
        data = {
            "id": 1,
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": "invalid",
            "description": "boundary touch",
            "amount": Decimal("0.30"),
        }
        with pytest.raises(ValidationError):
            PenaltyRecordRead.model_validate(data)

    def test_read_record_invalid_amount(self):
        data = {
            "id": 1,
            "routine_id": 1,
            "judge_id": 1,
            "judge_role": PenaltyJudgeRole.line_judge,
            "description": "boundary touch",
            "amount": "invalid",
        }
        with pytest.raises(ValidationError):
            PenaltyRecordRead.model_validate(data)

    def test_record_read_from_orm_object(self):
        class MockRecord:
            def __init__(self, id, routine_id, judge_id, judge_role, description, amount):
                self.id = id
                self.routine_id = routine_id
                self.judge_id = judge_id
                self.judge_role = judge_role
                self.description = description
                self.amount = amount

        mock_record = MockRecord(
            1, 1, 1, PenaltyJudgeRole.line_judge, "boundary touch", Decimal("0.30")
        )
        record_read = PenaltyRecordRead.model_validate(mock_record)
        assert record_read.id == 1
        assert record_read.routine_id == 1
        assert record_read.judge_id == 1
        assert record_read.judge_role == PenaltyJudgeRole.line_judge
        assert record_read.description == "boundary touch"
        assert record_read.amount == Decimal("0.30")
