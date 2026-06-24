import pytest
from pydantic import ValidationError

from app.schemas.meet import MeetCreate, MeetRead, MeetUpdate
from app.models import MeetStatus


class TestMeetCreate:
    def test_meet_create_allows_missing_district_id(self):
        meet = MeetCreate.model_validate(
            {
                "name": "Nationals",
                "location": "Main Arena",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            }
        )

        assert meet.district_id is None
        assert meet.status == MeetStatus.scheduled

    def test_meet_create_accepts_district_id(self):
        meet = MeetCreate.model_validate(
            {
                "district_id": 3,
                "name": "District Meet",
                "location": "Main Arena",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
            }
        )

        assert meet.district_id == 3

    def test_meet_create_rejects_non_positive_district_id(self):
        with pytest.raises(ValidationError):
            MeetCreate.model_validate(
                {
                    "district_id": 0,
                    "name": "Invalid Meet",
                    "location": "Main Arena",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-02",
                }
            )


class TestMeetUpdate:
    def test_meet_update_all_fields_optional(self):
        meet = MeetUpdate.model_validate({})

        assert meet.district_id is None
        assert meet.name is None
        assert meet.location is None
        assert meet.start_date is None
        assert meet.end_date is None
        assert meet.status is None

    def test_meet_update_accepts_district_id(self):
        meet = MeetUpdate.model_validate({"district_id": 5})

        assert meet.district_id == 5

    def test_meet_update_rejects_non_positive_district_id(self):
        with pytest.raises(ValidationError):
            MeetUpdate.model_validate({"district_id": -1})


class TestMeetRead:
    def test_meet_read_from_mapping(self):
        meet = MeetRead.model_validate(
            {
                "id": 1,
                "district_id": None,
                "name": "Nationals",
                "location": "Main Arena",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
                "status": MeetStatus.scheduled,
            }
        )

        assert meet.id == 1
        assert meet.district_id is None
        assert meet.status == MeetStatus.scheduled

    def test_meet_read_from_orm_like_object(self):
        class ORMObject:
            def __init__(self):
                self.id = 1
                self.district_id = 7
                self.name = "District Meet"
                self.location = "Main Arena"
                self.start_date = "2026-06-01"
                self.end_date = "2026-06-02"
                self.status = MeetStatus.scheduled

        meet = MeetRead.model_validate(ORMObject())

        assert meet.id == 1
        assert meet.district_id == 7
        assert meet.name == "District Meet"
