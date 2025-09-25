"""add timestamps to courses and lessons

Revision ID: d711a935715f
Revises: b743e6082bc3
Create Date: 2025-09-25 22:44:07.597978

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d711a935715f"
down_revision: Union[str, Sequence[str], None] = "b743e6082bc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns with server default to existing tables
    op.add_column(
        "courses",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "courses",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.add_column(
        "lessons",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # Note: updated_at will be managed by the ORM (SQLAlchemy onupdate=func.now()).
    # We intentionally avoid creating database triggers here.


def downgrade() -> None:
    # Drop columns
    op.drop_column("lessons", "updated_at")
    op.drop_column("lessons", "created_at")
    op.drop_column("courses", "updated_at")
    op.drop_column("courses", "created_at")
