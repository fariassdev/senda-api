"""add script_generated_at and audio_generated_at timestamps to lessons

Revision ID: a542040b2986
Revises: d711a935715f
Create Date: 2025-09-25 23:04:37.667517

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a542040b2986"
down_revision: Union[str, Sequence[str], None] = "d711a935715f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add script_generated_at and audio_generated_at timestamp columns to lessons table
    op.add_column(
        "lessons",
        sa.Column("script_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column("audio_generated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the timestamp columns
    op.drop_column("lessons", "audio_generated_at")
    op.drop_column("lessons", "script_generated_at")
