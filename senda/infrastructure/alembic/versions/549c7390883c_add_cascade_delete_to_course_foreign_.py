"""add cascade delete to course foreign keys

Revision ID: 549c7390883c
Revises: 666cc53a93be
Create Date: 2025-12-19 14:02:46.014016

"""

from collections.abc import Sequence

from alembic import op

revision: str = "549c7390883c"
down_revision: str | None = "666cc53a93be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop existing foreign key constraints and recreate with ON DELETE CASCADE

    # 1. lesson.course_id -> course.id
    op.drop_constraint("lesson_course_id_fkey", "lesson", type_="foreignkey")
    op.create_foreign_key(
        "lesson_course_id_fkey",
        "lesson",
        "course",
        ["course_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. course_tag.course_id -> course.id
    op.drop_constraint("course_tag_course_id_fkey", "course_tag", type_="foreignkey")
    op.create_foreign_key(
        "course_tag_course_id_fkey",
        "course_tag",
        "course",
        ["course_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. favorite.course_id -> course.id
    op.drop_constraint("favorite_course_id_fkey", "favorite", type_="foreignkey")
    op.create_foreign_key(
        "favorite_course_id_fkey",
        "favorite",
        "course",
        ["course_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert to foreign keys without CASCADE

    # 1. lesson.course_id
    op.drop_constraint("lesson_course_id_fkey", "lesson", type_="foreignkey")
    op.create_foreign_key(
        "lesson_course_id_fkey", "lesson", "course", ["course_id"], ["id"]
    )

    # 2. course_tag.course_id
    op.drop_constraint("course_tag_course_id_fkey", "course_tag", type_="foreignkey")
    op.create_foreign_key(
        "course_tag_course_id_fkey", "course_tag", "course", ["course_id"], ["id"]
    )

    # 3. favorite.course_id
    op.drop_constraint("favorite_course_id_fkey", "favorite", type_="foreignkey")
    op.create_foreign_key(
        "favorite_course_id_fkey", "favorite", "course", ["course_id"], ["id"]
    )
