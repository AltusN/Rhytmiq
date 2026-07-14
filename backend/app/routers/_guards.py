"""
Common helpers for routers
"""

from fastapi import HTTPException, status

from app.models import Meet, MeetStatus


def ensure_meet_not_completed(meet: Meet) -> None:
    if meet.status == MeetStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meet {meet.id} is completed and cannot be modified",
        )
