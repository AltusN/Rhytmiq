"""replace level enum with full competitive taxonomy

Revision ID: e67c22245dbc
Revises: 7f9486184787
Create Date: 2026-07-12 15:25:40.427113

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e67c22245dbc"
down_revision: str | Sequence[str] | None = "7f9486184787"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enum swaps aren't autogenerate-able, so this is hand-written. Every value
    # currently in use (level_1-5, junior, senior) keeps its exact string in the new
    # taxonomy, so the ::text::level cast below is safe -- it only fails if a row holds
    # a retired value (elite_1/elite_2/junior_elite), which none do today.
    op.execute("ALTER TYPE level RENAME TO level_old")
    op.execute(
        "CREATE TYPE level AS ENUM ("
        "'level_1','level_2','level_3','level_4','level_5','level_6','level_7',"
        "'level_8','level_9','level_10','high_performance_1','high_performance_2',"
        "'high_performance_3','high_performance_4','pre_junior','junior','senior',"
        "'olympic')"
    )
    op.execute("ALTER TABLE meet_entries ALTER COLUMN level TYPE level USING level::text::level")
    op.execute(
        "ALTER TABLE routine_profiles ALTER COLUMN level TYPE level USING level::text::level"
    )
    op.execute("DROP TYPE level_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE level RENAME TO level_old")
    op.execute(
        "CREATE TYPE level AS ENUM ("
        "'level_1','level_2','level_3','level_4','level_5','elite_1','elite_2',"
        "'junior_elite','junior','senior')"
    )
    op.execute("ALTER TABLE meet_entries ALTER COLUMN level TYPE level USING level::text::level")
    op.execute(
        "ALTER TABLE routine_profiles ALTER COLUMN level TYPE level USING level::text::level"
    )
    op.execute("DROP TYPE level_old")
