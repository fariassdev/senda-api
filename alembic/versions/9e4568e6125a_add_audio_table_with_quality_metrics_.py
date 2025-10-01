"""add audio table with quality metrics and remove audio fields from lesson

Revision ID: 9e4568e6125a
Revises: 68811a19dc31
Create Date: 2025-10-01 18:24:26.305758

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9e4568e6125a"
down_revision: Union[str, Sequence[str], None] = "68811a19dc31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audios table and remove audio fields from lessons table."""

    # Create audios table
    op.create_table(
        "audios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "lesson_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lessons.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("file_size_mb", sa.Float(), nullable=False),
        # Duration metrics
        sa.Column("total_duration_seconds", sa.Float(), nullable=False),
        sa.Column("expected_duration_seconds", sa.Float(), nullable=False),
        sa.Column("duration_match_percentage", sa.Float(), nullable=False),
        # Speech/Silence metrics
        sa.Column("speech_duration_seconds", sa.Float(), nullable=False),
        sa.Column("silence_duration_seconds", sa.Float(), nullable=False),
        sa.Column("speech_to_silence_ratio", sa.Float(), nullable=False),
        sa.Column("speech_percentage", sa.Float(), nullable=False),
        # Silence analysis
        sa.Column("silence_segment_count", sa.Integer(), nullable=False),
        sa.Column("longest_silence_seconds", sa.Float(), nullable=False),
        sa.Column("average_silence_seconds", sa.Float(), nullable=False),
        # Speech analysis
        sa.Column("speech_segment_count", sa.Integer(), nullable=False),
        sa.Column("expected_speech_segment_count", sa.Integer(), nullable=False),
        # Audio quality
        sa.Column("average_loudness_dbfs", sa.Float(), nullable=False),
        sa.Column("peak_loudness_dbfs", sa.Float(), nullable=False),
        sa.Column("dynamic_range_db", sa.Float(), nullable=False),
        # Validation flags
        sa.Column("is_duration_valid", sa.Boolean(), nullable=False),
        sa.Column("is_speech_ratio_valid", sa.Boolean(), nullable=False),
        sa.Column("is_silence_gaps_valid", sa.Boolean(), nullable=False),
        sa.Column("is_segment_count_valid", sa.Boolean(), nullable=False),
        sa.Column("is_loudness_valid", sa.Boolean(), nullable=False),
        sa.Column("is_file_size_valid", sa.Boolean(), nullable=False),
        sa.Column("is_quality_valid", sa.Boolean(), nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Create index on lesson_id for faster lookups
    op.create_index("ix_audios_lesson_id", "audios", ["lesson_id"], unique=True)

    # Remove audio_url and audio_generated_at columns from lessons table
    op.drop_column("lessons", "audio_url")
    op.drop_column("lessons", "audio_generated_at")


def downgrade() -> None:
    """Restore audio fields to lessons table and drop audios table."""

    # Add back audio fields to lessons table
    op.add_column("lessons", sa.Column("audio_url", sa.String(), nullable=True))
    op.add_column(
        "lessons",
        sa.Column("audio_generated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Drop audios table
    op.drop_index("ix_audios_lesson_id", table_name="audios")
    op.drop_table("audios")
