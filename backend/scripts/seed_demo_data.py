"""Populate the active database with a small, varied demo dataset.

Targets whatever POSTGRESQL_DATABASE_URL is active (see app/db.py). Not idempotent by
design: run it once against a freshly migrated database (`make dev && make seed`), and
use `make reset` to wipe and start over rather than re-running this against a populated DB.
"""

from datetime import date

from app.db import SessionLocal
from app.models import (
    AgeGroup,
    Apparatus,
    Club,
    Coach,
    District,
    Group,
    Gymnast,
    Level,
    Meet,
    MeetEntry,
    MeetStatus,
    Routine,
    RoutineProfile,
)


def run() -> None:
    db = SessionLocal()
    try:
        # -- Districts --
        district_north = District(name="Northern District", abbreviation="NORTH")
        district_south = District(name="Southern District", abbreviation="SOUTH")
        db.add_all([district_north, district_south])
        db.flush()

        # -- Clubs --
        club_starlight = Club(
            district_id=district_north.id, name="Starlight Gymnastics", abbreviation="STAR"
        )
        club_aurora = Club(
            district_id=district_north.id, name="Aurora Rhythmic", abbreviation="AURO"
        )
        club_riverside = Club(
            district_id=district_south.id, name="Riverside Gymnastics Club", abbreviation="RIVR"
        )
        db.add_all([club_starlight, club_aurora, club_riverside])
        db.flush()

        # -- Coaches --
        db.add_all(
            [
                Coach(
                    club_id=club_starlight.id,
                    first_name="Elena",
                    last_name="Volkova",
                    is_head_coach=True,
                ),
                Coach(
                    club_id=club_starlight.id,
                    first_name="Maria",
                    last_name="Ionescu",
                    is_head_coach=False,
                ),
                Coach(
                    club_id=club_aurora.id,
                    first_name="Sofia",
                    last_name="Kowalski",
                    is_head_coach=True,
                ),
                Coach(
                    club_id=club_riverside.id,
                    first_name="Grace",
                    last_name="Nakamura",
                    is_head_coach=True,
                ),
            ]
        )

        # -- Groups --
        group_junior_star = Group(club_id=club_starlight.id, name="Junior Ensemble")
        group_senior_aurora = Group(club_id=club_aurora.id, name="Senior Ensemble")
        db.add_all([group_junior_star, group_senior_aurora])
        db.flush()

        # -- Gymnasts --
        # Club-affiliated, no group
        gymnast_anna = Gymnast(
            club_id=club_starlight.id,
            first_name="Anna",
            last_name="Petrova",
            date_of_birth=date(2013, 4, 12),
            country_code="BLR",
        )
        gymnast_maya = Gymnast(
            club_id=club_riverside.id,
            first_name="Maya",
            last_name="Chen",
            date_of_birth=date(2011, 9, 3),
            country_code="USA",
        )
        # Club + group affiliated (group ensemble members)
        gymnast_lena = Gymnast(
            club_id=club_starlight.id,
            group_id=group_junior_star.id,
            first_name="Lena",
            last_name="Popova",
            date_of_birth=date(2014, 1, 20),
            country_code="BLR",
        )
        gymnast_kira = Gymnast(
            club_id=club_starlight.id,
            group_id=group_junior_star.id,
            first_name="Kira",
            last_name="Sokolova",
            date_of_birth=date(2014, 6, 15),
            country_code="BLR",
        )
        gymnast_olivia = Gymnast(
            club_id=club_aurora.id,
            group_id=group_senior_aurora.id,
            first_name="Olivia",
            last_name="Nowak",
            date_of_birth=date(2009, 11, 2),
            country_code="POL",
        )
        gymnast_zara = Gymnast(
            club_id=club_aurora.id,
            group_id=group_senior_aurora.id,
            first_name="Zara",
            last_name="Kowalczyk",
            date_of_birth=date(2010, 3, 8),
            country_code="POL",
        )
        # Standalone gymnast, no club at all
        gymnast_freelance = Gymnast(
            first_name="Isabella",
            last_name="Marino",
            date_of_birth=date(2012, 7, 30),
            country_code="ITA",
        )
        db.add_all(
            [
                gymnast_anna,
                gymnast_maya,
                gymnast_lena,
                gymnast_kira,
                gymnast_olivia,
                gymnast_zara,
                gymnast_freelance,
            ]
        )
        db.flush()

        # -- Meets: one of every MeetStatus --
        meet_draft = Meet(
            district_id=district_north.id,
            name="Autumn Invitational",
            location="Northern Sports Hall",
            start_date=date(2026, 10, 3),
            end_date=date(2026, 10, 4),
            status=MeetStatus.draft,
        )
        meet_scheduled = Meet(
            district_id=district_north.id,
            name="Winter Classic",
            location="Starlight Arena",
            start_date=date(2026, 12, 12),
            end_date=date(2026, 12, 13),
            status=MeetStatus.scheduled,
        )
        meet_in_progress = Meet(
            district_id=district_south.id,
            name="Summer Championship",
            location="Riverside Convention Center",
            start_date=date(2026, 7, 4),
            end_date=date(2026, 7, 5),
            status=MeetStatus.in_progress,
        )
        meet_completed = Meet(
            district_id=district_south.id,
            name="Spring Open",
            location="Riverside Gymnasium",
            start_date=date(2026, 4, 18),
            end_date=date(2026, 4, 19),
            status=MeetStatus.completed,
        )
        # No district (SET NULL case) and cancelled
        meet_cancelled = Meet(
            district_id=None,
            name="Regional Qualifier",
            location="TBD",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 2),
            status=MeetStatus.cancelled,
        )
        db.add_all([meet_draft, meet_scheduled, meet_in_progress, meet_completed, meet_cancelled])
        db.flush()

        # -- Meet entries: mix of individual and group entries --
        entry_anna_inprogress = MeetEntry(
            meet_id=meet_in_progress.id,
            gymnast_id=gymnast_anna.id,
            bib_number="101",
            age_group=AgeGroup.under_14,
            level=Level.level_4,
        )
        entry_maya_inprogress = MeetEntry(
            meet_id=meet_in_progress.id,
            gymnast_id=gymnast_maya.id,
            bib_number="102",
            age_group=AgeGroup.under_14,
            level=Level.level_5,
        )
        entry_group_junior_inprogress = MeetEntry(
            meet_id=meet_in_progress.id,
            group_id=group_junior_star.id,
            bib_number="G1",
            age_group=AgeGroup.under_14,
            level=Level.level_3,
        )
        entry_anna_completed = MeetEntry(
            meet_id=meet_completed.id,
            gymnast_id=gymnast_anna.id,
            bib_number="201",
            age_group=AgeGroup.under_14,
            level=Level.level_4,
        )
        entry_group_senior_completed = MeetEntry(
            meet_id=meet_completed.id,
            group_id=group_senior_aurora.id,
            bib_number="G2",
            age_group=AgeGroup.over_14,
            level=Level.senior,
        )
        entry_freelance_scheduled = MeetEntry(
            meet_id=meet_scheduled.id,
            gymnast_id=gymnast_freelance.id,
            bib_number="301",
            age_group=AgeGroup.under_14,
            level=Level.level_3,
        )
        db.add_all(
            [
                entry_anna_inprogress,
                entry_maya_inprogress,
                entry_group_junior_inprogress,
                entry_anna_completed,
                entry_group_senior_completed,
                entry_freelance_scheduled,
            ]
        )
        db.flush()

        # -- Routine profiles: gymnast-scoped and group-scoped --
        # Matches entry_anna_inprogress (apparatus=ball, level=level_4) so Routine.music_url
        # resolves live for that routine below.
        profile_anna_ball = RoutineProfile(
            gymnast_id=gymnast_anna.id,
            apparatus=Apparatus.ball,
            level=Level.level_4,
            music_url="https://example.com/music/anna-ball.mp3",
            choreography_notes="Lyrical opening, tempo increases at 0:45.",
        )
        profile_anna_hoop = RoutineProfile(
            gymnast_id=gymnast_anna.id,
            apparatus=Apparatus.hoop,
            level=Level.level_4,
            music_url="https://example.com/music/anna-hoop.mp3",
        )
        # Matches entry_group_junior_inprogress (apparatus=clubs, level=level_3)
        profile_junior_group_clubs = RoutineProfile(
            group_id=group_junior_star.id,
            apparatus=Apparatus.clubs,
            level=Level.level_3,
            music_url="https://example.com/music/junior-ensemble-clubs.mp3",
            choreography_notes="Synchronized clubs exchange at center, formation change at 1:10.",
        )
        db.add_all([profile_anna_ball, profile_anna_hoop, profile_junior_group_clubs])
        db.flush()

        # -- Routines: one or more apparatus per entry --
        db.add_all(
            [
                # Resolves music_url via profile_anna_ball above.
                Routine(
                    entry_id=entry_anna_inprogress.id,
                    apparatus=Apparatus.ball,
                    order_of_performance=1,
                ),
                # No matching profile (ribbon) -> music_url resolves to None.
                Routine(
                    entry_id=entry_anna_inprogress.id,
                    apparatus=Apparatus.ribbon,
                    order_of_performance=2,
                ),
                Routine(
                    entry_id=entry_maya_inprogress.id,
                    apparatus=Apparatus.rope,
                    order_of_performance=1,
                ),
                # Resolves music_url via profile_junior_group_clubs above.
                Routine(
                    entry_id=entry_group_junior_inprogress.id,
                    apparatus=Apparatus.clubs,
                    order_of_performance=1,
                ),
                Routine(
                    entry_id=entry_anna_completed.id,
                    apparatus=Apparatus.freehand,
                    order_of_performance=1,
                ),
                Routine(
                    entry_id=entry_group_senior_completed.id,
                    apparatus=Apparatus.hoop,
                    order_of_performance=1,
                ),
                Routine(
                    entry_id=entry_freelance_scheduled.id,
                    apparatus=Apparatus.ribbon,
                    order_of_performance=1,
                ),
            ]
        )

        db.commit()
        print("Demo data seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
