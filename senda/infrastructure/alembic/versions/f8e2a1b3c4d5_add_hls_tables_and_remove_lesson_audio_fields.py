"""add_hls_tables_and_remove_lesson_audio_fields

Revision ID: f8e2a1b3c4d5
Revises: 78561938c0a9
Create Date: 2026-06-08 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8e2a1b3c4d5"
down_revision: Union[str, None] = "78561938c0a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.create_table(
        "lesson_audio",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("voice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voice_slug", sa.String(length=255), nullable=True),
        sa.Column("audio_provider", sa.String(length=50), nullable=True),
        sa.Column("playlist_url", sa.String(), nullable=False),
        sa.Column("hls_base_path", sa.String(), nullable=False),
        sa.Column("segment_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lesson.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voice_id"], ["voices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "voice_id", name="uq_lesson_audio_voice"),
    )
    op.create_index("idx_lesson_audio_lesson_id", "lesson_audio", ["lesson_id"])

    op.create_table(
        "audio_generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("voice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voice_slug", sa.String(length=255), nullable=True),
        sa.Column("audio_provider", sa.String(length=50), nullable=True),
        sa.Column("s3_base_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column(
            "segments_available", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("segment_count", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("lesson_audio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lesson.id"]),
        sa.ForeignKeyConstraint(["voice_id"], ["voices.id"]),
        sa.ForeignKeyConstraint(["lesson_audio_id"], ["lesson_audio.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_audio_generation_jobs_lesson_created",
        "audio_generation_jobs",
        ["lesson_id", "created_at"],
    )
    op.create_index(
        "uq_active_job_per_lesson_voice",
        "audio_generation_jobs",
        ["lesson_id", "voice_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'GENERATING')"),
    )

    op.drop_constraint("fk_lesson_voice_id_voices", "lesson", type_="foreignkey")
    op.drop_column("lesson", "voice_id")
    op.drop_column("lesson", "audio_generated_at")
    op.drop_column("lesson", "audio_url")


def downgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.add_column("lesson", sa.Column("audio_url", sa.String(), nullable=True))
    op.add_column(
        "lesson", sa.Column("audio_generated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "lesson", sa.Column("voice_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_lesson_voice_id_voices", "lesson", "voices", ["voice_id"], ["id"]
    )

    op.drop_index("uq_active_job_per_lesson_voice", table_name="audio_generation_jobs")
    op.drop_index(
        "idx_audio_generation_jobs_lesson_created", table_name="audio_generation_jobs"
    )
    op.drop_table("audio_generation_jobs")
    op.drop_index("idx_lesson_audio_lesson_id", table_name="lesson_audio")
    op.drop_table("lesson_audio")
