"""add_needs_regeneration_to_lessons

Revision ID: 436077101d0c
Revises: 68811a19dc31
Create Date: 2025-10-02 03:06:41.384884

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "436077101d0c"
down_revision: Union[str, Sequence[str], None] = "68811a19dc31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "lessons",
        sa.Column(
            "needs_regeneration", sa.Boolean(), server_default="false", nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("lessons", "needs_regeneration")
