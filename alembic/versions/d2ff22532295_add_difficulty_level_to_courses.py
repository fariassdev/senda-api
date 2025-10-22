"""add_difficulty_level_to_courses

Revision ID: d2ff22532295
Revises: 68811a19dc31
Create Date: 2025-10-23 01:06:49.771720

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2ff22532295"
down_revision: Union[str, Sequence[str], None] = "68811a19dc31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "courses",
        sa.Column(
            "difficulty_level", sa.String, nullable=False, server_default="BEGINNER"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("courses", "difficulty_level")
