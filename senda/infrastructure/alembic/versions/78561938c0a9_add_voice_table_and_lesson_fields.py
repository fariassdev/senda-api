"""add_voice_table_and_lesson_fields

Revision ID: 78561938c0a9
Revises: 549c7390883c
Create Date: 2026-05-27 15:47:12.842642

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78561938c0a9"
down_revision: Union[str, None] = "549c7390883c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy.dialects import postgresql

    op.create_table(
        "voices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "language", sa.String(length=10), nullable=False, server_default="es"
        ),
        sa.Column("gender", sa.String(length=20), nullable=False),
        sa.Column("reference_s3_key", sa.String(length=500), nullable=False),
        sa.Column("sample_s3_key", sa.String(length=500), nullable=True),
        sa.Column("exaggeration", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("cfg_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.4"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "is_synced_to_modal", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("modal_sync_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_voices_slug", "voices", ["slug"])
    op.create_index("idx_voices_is_active", "voices", ["is_active"])

    op.add_column(
        "lesson", sa.Column("voice_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "lesson", sa.Column("voice_slug", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "lesson", sa.Column("audio_provider", sa.String(length=50), nullable=True)
    )
    op.create_foreign_key(
        "fk_lesson_voice_id_voices", "lesson", "voices", ["voice_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_lesson_voice_id_voices", "lesson", type_="foreignkey")
    op.drop_column("lesson", "audio_provider")
    op.drop_column("lesson", "voice_slug")
    op.drop_column("lesson", "voice_id")
    op.drop_index("idx_voices_is_active", table_name="voices")
    op.drop_index("idx_voices_slug", table_name="voices")
    op.drop_table("voices")
