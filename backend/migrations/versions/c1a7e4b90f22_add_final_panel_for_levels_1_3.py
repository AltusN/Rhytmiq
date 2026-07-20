"""add_final_panel_for_levels_1_3

Revision ID: c1a7e4b90f22
Revises: b3f1c9d47e20
Create Date: 2026-07-20 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a7e4b90f22"
down_revision: str | Sequence[str] | None = "b3f1c9d47e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CAP = "panel IN ('difficulty_body', 'difficulty_apparatus') OR value <= 10"
_NEW_CAP = (
    "CASE panel "
    "WHEN 'difficulty_body' THEN true "
    "WHEN 'difficulty_apparatus' THEN true "
    "WHEN 'final' THEN value <= 13 "
    "ELSE value <= 10 END"
)


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate never sees a new enum value (see CLAUDE.md), so this is hand-written.
    # The extra wrinkle: Postgres refuses to *use* an enum value in the same transaction
    # that added it, and the CHECK constraint below references the literal 'final'.
    # autocommit_block() commits the ALTER TYPE in its own transaction first.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE panel ADD VALUE IF NOT EXISTS 'final'")

    op.drop_constraint("ck_judge_score_panel_value_cap", "judge_scores", type_="check")
    op.create_check_constraint("ck_judge_score_panel_value_cap", "judge_scores", _NEW_CAP)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the constraint BEFORE rebuilding the type: it references 'final', which the
    # rebuilt type will not have.
    op.drop_constraint("ck_judge_score_panel_value_cap", "judge_scores", type_="check")

    # Postgres cannot remove a value from an enum -- the type must be rebuilt. This
    # fails loudly if any judge_scores row still sits on 'final', which is correct:
    # such a row has no representation in the old schema.
    op.execute("ALTER TYPE panel RENAME TO panel_old")
    op.execute(
        "CREATE TYPE panel AS ENUM "
        "('difficulty_body', 'difficulty_apparatus', 'execution', 'artistry')"
    )
    op.execute("ALTER TABLE judge_scores ALTER COLUMN panel TYPE panel USING panel::text::panel")
    op.execute("DROP TYPE panel_old")

    op.create_check_constraint("ck_judge_score_panel_value_cap", "judge_scores", _OLD_CAP)
