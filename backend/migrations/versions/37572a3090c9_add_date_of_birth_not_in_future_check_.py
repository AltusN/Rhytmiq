"""add date_of_birth not-in-future check constraint to gymnasts

Revision ID: 37572a3090c9
Revises: 5f281affff03
Create Date: 2026-07-09 08:40:36.309923

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37572a3090c9"
down_revision: str | Sequence[str] | None = "5f281affff03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_gymnast_date_of_birth_valid",
        "gymnasts",
        "date_of_birth <= current_date",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_gymnast_date_of_birth_valid", "gymnasts", type_="check")
