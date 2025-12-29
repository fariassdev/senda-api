"""add generation_jobs table

Revision ID: a1b2c3d4e5f6
Revises: 549c7390883c
Create Date: 2025-12-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "549c7390883c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_job",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payload", JSONB(), nullable=True),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lesson.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes as per AC#1 requirements
    op.create_index("idx_generation_job_status", "generation_job", ["status"])
    op.create_index("idx_generation_job_course_id", "generation_job", ["course_id"])
    op.create_index(
        "idx_generation_job_created_at", "generation_job", [sa.text("created_at DESC")]
    )


def downgrade() -> None:
    op.drop_index("idx_generation_job_created_at", table_name="generation_job")
    op.drop_index("idx_generation_job_course_id", table_name="generation_job")
    op.drop_index("idx_generation_job_status", table_name="generation_job")
    op.drop_table("generation_job")
