"""add_speed_to_audio_generation_jobs

Revision ID: a3c7d9e1f2b4
Revises: f8e2a1b3c4d5
Create Date: 2026-06-08 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3c7d9e1f2b4"
down_revision: Union[str, None] = "f8e2a1b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audio_generation_jobs",
        sa.Column("speed", sa.Float(), nullable=False, server_default="1.0"),
    )


def downgrade() -> None:
    op.drop_column("audio_generation_jobs", "speed")
