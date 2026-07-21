"""
Results router — read-only reporting for /meets/{meet_id}/standings and
/meets/{meet_id}/all-around.

Design notes:
- Deliberately not CRUD-shaped like every other router: these are computed views over
  existing data, not a resource with its own table, so there's no POST/PATCH/DELETE.
- Both endpoints compute live off compute_routine_score / rank_apparatus / rank_all_around
  (app/scoring.py) on every call rather than snapshotting a result -- same "resolve live,
  don't snapshot" philosophy as Routine.music_url and GET /routines/{id}/score.
- `provisional` is true unless meet.status == MeetStatus.completed, so callers can tell a
  mid-meet standings snapshot from the final one.
- /standings requires `apparatus` (a per-apparatus ranking is undefined without one);
  /all-around has no apparatus filter since it deliberately spans all of them. Both accept
  optional `level`/`age_group` filters, applied against MeetEntry, matching meet_entry.py's
  filter style.
- A missing meet is the only 404 case; an empty category returns 200 with `rankings: []`.
- `medal` on each row is additive to `rank`, and which system produces it depends on the
  row's level band (app/scoring.py):
  - **Levels 1-3** use the meet's configured `medal_gold_min`/`medal_silver_min` score
    cutoffs, answering "did this total clear a threshold". Those cutoffs are scaled for
    the levels 1-3 ALL-AROUND (2 apparatus, max 26), so they are meaningful ONLY on
    /all-around: on the per-apparatus /standings endpoint a cutoff-band row's `medal` is
    always null (a single 0-13 routine can't clear an all-around cutoff, so scoring it
    would mark everyone bronze -- see `_apparatus_medal`). Both cutoffs null (the default)
    means the meet isn't using them, so those rows' `medal` is null everywhere.
  - **Levels 4+** use placement: the first three distinct ranks, ties sharing a medal
    (see `assign_placement_medals`). No configuration needed.
  Placement medals are assigned over the rankings actually returned, so -- exactly like
  `rank` itself -- they are only meaningful when the caller has filtered to a single
  (level, age_group) slice.
- These endpoints iterate every routine in a meet on every call (compute_routine_score reads
  routine.judge_scores), so -- unlike the single-row CRUD endpoints elsewhere in this
  codebase -- they eager-load with selectinload to avoid an N+1 over the whole meet.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import AgeGroup, Apparatus, Level, Meet, MeetEntry, MeetStatus, Routine
from app.schemas.results import (
    AllAroundStandingRow,
    AllAroundStandingsRead,
    ApparatusStandingRow,
    ApparatusStandingsRead,
)
from app.scoring import (
    Medal,
    MedalMode,
    assign_placement_medals,
    medal_for_total,
    profile_for_level,
    rank_all_around,
    rank_apparatus,
)

router = APIRouter(prefix="/meets", tags=["Results"])


def _competitor_name(entry: MeetEntry) -> str:
    if entry.gymnast_id is not None:
        return f"{entry.gymnast.first_name} {entry.gymnast.last_name}"
    group = entry.group
    assert group is not None
    return group.name


def _medal_for(level: Level, total: Decimal, placement: Medal | None, meet: Meet) -> Medal | None:
    """Cutoffs at levels 1-3, placement at 4+ -- see the module docstring."""
    if profile_for_level(level).medal_mode is MedalMode.cutoff:
        return medal_for_total(total, meet.medal_gold_min, meet.medal_silver_min)
    return placement


def _apparatus_medal(
    level: Level, total: Decimal, placement: Medal | None, meet: Meet
) -> Medal | None:
    """
    Medal for a per-apparatus /standings row. Placement bands medal exactly as on the
    all-around, but CUTOFF bands (levels 1-3) return None here: their cutoffs are scaled
    for the 2-apparatus all-around (max 26), so applying them to a single 0-13 routine
    would mark every competitor bronze -- misleading. Levels 1-3 only earn a cutoff medal
    on /all-around, where the scale matches.
    """
    if profile_for_level(level).medal_mode is MedalMode.cutoff:
        return None
    return _medal_for(level, total, placement, meet)


@router.get("/{meet_id}/standings", response_model=ApparatusStandingsRead)
def get_apparatus_standings(
    meet_id: int,
    db: Annotated[Session, Depends(get_db)],
    apparatus: Annotated[Apparatus, Query(description="Apparatus to rank (required).")],
    level: Annotated[Level | None, Query(description="Filter by level")] = None,
    age_group: Annotated[AgeGroup | None, Query(description="Filter by age_group")] = None,
) -> ApparatusStandingsRead:
    meet = db.get(Meet, meet_id)
    if meet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Meet with id {meet_id} not found"
        )

    query = (
        db.query(Routine)
        .join(MeetEntry)
        .filter(MeetEntry.meet_id == meet_id, Routine.apparatus == apparatus)
        .options(selectinload(Routine.judge_scores))
    )
    if level is not None:
        query = query.filter(MeetEntry.level == level)
    if age_group is not None:
        query = query.filter(MeetEntry.age_group == age_group)

    standings = rank_apparatus(query.all())
    placements = assign_placement_medals([standing.rank for standing in standings])

    return ApparatusStandingsRead(
        meet_id=meet_id,
        provisional=meet.status != MeetStatus.completed,
        apparatus=apparatus,
        level=level,
        age_group=age_group,
        rankings=[
            ApparatusStandingRow(
                rank=standing.rank,
                entry_id=standing.routine.entry_id,
                routine_id=standing.routine.id,
                competitor_name=_competitor_name(standing.routine.entry),
                bib_number=standing.routine.entry.bib_number,
                level=standing.routine.entry.level,
                age_group=standing.routine.entry.age_group,
                apparatus=standing.routine.apparatus,
                d_score=standing.score.d_score,
                a_score=standing.score.a_score,
                e_score=standing.score.e_score,
                final_score=standing.score.final_score,
                penalty=standing.score.penalty,
                total=standing.score.total,
                medal=_apparatus_medal(
                    standing.routine.entry.level,
                    standing.score.total,
                    placements[index],
                    meet,
                ),
            )
            for index, standing in enumerate(standings)
        ],
    )


@router.get("/{meet_id}/all-around", response_model=AllAroundStandingsRead)
def get_all_around_standings(
    meet_id: int,
    db: Annotated[Session, Depends(get_db)],
    level: Annotated[Level | None, Query(description="Filter by level")] = None,
    age_group: Annotated[AgeGroup | None, Query(description="Filter by age_group")] = None,
) -> AllAroundStandingsRead:
    meet = db.get(Meet, meet_id)
    if meet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Meet with id {meet_id} not found"
        )

    query = (
        db.query(MeetEntry)
        .filter(MeetEntry.meet_id == meet_id)
        .options(
            selectinload(MeetEntry.routines).selectinload(Routine.judge_scores),
            selectinload(MeetEntry.gymnast),
            selectinload(MeetEntry.group),
        )
    )
    if level is not None:
        query = query.filter(MeetEntry.level == level)
    if age_group is not None:
        query = query.filter(MeetEntry.age_group == age_group)

    standings = rank_all_around(query.all())
    placements = assign_placement_medals([standing.rank for standing in standings])

    return AllAroundStandingsRead(
        meet_id=meet_id,
        provisional=meet.status != MeetStatus.completed,
        level=level,
        age_group=age_group,
        rankings=[
            AllAroundStandingRow(
                rank=standing.rank,
                entry_id=standing.entry.id,
                competitor_name=_competitor_name(standing.entry),
                bib_number=standing.entry.bib_number,
                level=standing.entry.level,
                age_group=standing.entry.age_group,
                total=standing.total,
                e_total=standing.e_total,
                routines_counted=standing.routines_counted,
                medal=_medal_for(standing.entry.level, standing.total, placements[index], meet),
            )
            for index, standing in enumerate(standings)
        ],
    )
