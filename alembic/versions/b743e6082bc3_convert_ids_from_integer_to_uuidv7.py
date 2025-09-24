"""Convert IDs from Integer to UUIDv7

This migration converts all integer primary keys and foreign keys to UUIDv7.
It preserves existing data by generating new UUIDs for all records while
maintaining relationships between courses and lessons.

Revision ID: b743e6082bc3
Revises: ea0874bf8805
Create Date: 2025-09-24 12:58:36.481189

"""

from typing import Sequence, Union
import uuid
import time

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b743e6082bc3"
down_revision: Union[str, Sequence[str], None] = "ea0874bf8805"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_uuidv7() -> str:
    """Generate UUIDv7 for migration."""
    timestamp_ms = int(time.time() * 1000)

    # Use a full random UUID's bytes as entropy
    rand = uuid.uuid4().bytes

    # Pack timestamp (48 bits / 6 bytes)
    timestamp_bytes = timestamp_ms.to_bytes(6, byteorder="big")

    # time_hi_and_version: set version 7 in the high nibble
    # take a random nibble from the random bytes to mix
    version_byte = 0x70 | (rand[6] & 0x0F)

    # clock_seq_hi_and_reserved: set the RFC 4122 variant (10xxxxxx)
    variant_byte = 0x80 | (rand[8] & 0x3F)

    # Construct 16 bytes: 6 bytes timestamp, 1 version, 1 rand, 1 variant, 7 rand
    uuid_bytes = (
        timestamp_bytes
        + bytes([version_byte])
        + bytes([rand[7]])
        + bytes([variant_byte])
        + rand[9:16]
    )

    # Ensure length is 16
    if len(uuid_bytes) != 16:
        raise RuntimeError(
            f"Generated UUID bytes length is {len(uuid_bytes)}, expected 16"
        )

    return str(uuid.UUID(bytes=uuid_bytes))


def upgrade() -> None:
    """Upgrade schema."""
    # Enable UUID extension in PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create a temporary mapping table for course IDs
    op.execute("""
        CREATE TEMPORARY TABLE course_id_mapping (
            old_id INTEGER,
            new_id UUID
        )
    """)

    # Create a temporary mapping table for lesson IDs
    op.execute("""
        CREATE TEMPORARY TABLE lesson_id_mapping (
            old_id INTEGER,
            new_id UUID
        )
    """)

    # Generate new UUIDs for all existing courses and store the mapping
    connection = op.get_bind()
    courses_result = connection.execute(sa.text("SELECT id FROM courses ORDER BY id"))

    for row in courses_result:
        old_id = row[0]
        new_id = generate_uuidv7()
        connection.execute(
            sa.text(
                "INSERT INTO course_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"
            ),
            {"old_id": old_id, "new_id": new_id},
        )

    # Generate new UUIDs for all existing lessons and store the mapping
    lessons_result = connection.execute(sa.text("SELECT id FROM lessons ORDER BY id"))

    for row in lessons_result:
        old_id = row[0]
        new_id = generate_uuidv7()
        connection.execute(
            sa.text(
                "INSERT INTO lesson_id_mapping (old_id, new_id) VALUES (:old_id, :new_id)"
            ),
            {"old_id": old_id, "new_id": new_id},
        )

    # Add new UUID columns to courses table
    op.add_column(
        "courses", sa.Column("id_new", postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Update courses with new UUIDs
    op.execute("""
        UPDATE courses 
        SET id_new = course_id_mapping.new_id 
        FROM course_id_mapping 
        WHERE courses.id = course_id_mapping.old_id
    """)

    # Add new UUID columns to lessons table
    op.add_column(
        "lessons", sa.Column("id_new", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "lessons",
        sa.Column("course_id_new", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Update lessons with new UUIDs
    op.execute("""
        UPDATE lessons 
        SET id_new = lesson_id_mapping.new_id 
        FROM lesson_id_mapping 
        WHERE lessons.id = lesson_id_mapping.old_id
    """)

    # Update lesson course_id references
    op.execute("""
        UPDATE lessons 
        SET course_id_new = course_id_mapping.new_id 
        FROM course_id_mapping 
        WHERE lessons.course_id = course_id_mapping.old_id
    """)

    # Drop existing constraints and indexes
    op.drop_constraint("lessons_course_id_fkey", "lessons", type_="foreignkey")
    op.drop_index("ix_lessons_id", table_name="lessons")
    op.drop_index("ix_courses_id", table_name="courses")

    # Drop old columns
    op.drop_column("lessons", "course_id")
    op.drop_column("lessons", "id")
    op.drop_column("courses", "id")

    # Rename new columns to original names
    op.alter_column("courses", "id_new", new_column_name="id")
    op.alter_column("lessons", "id_new", new_column_name="id")
    op.alter_column("lessons", "course_id_new", new_column_name="course_id")

    # Make the new UUID columns non-nullable
    op.alter_column("courses", "id", nullable=False)
    op.alter_column("lessons", "id", nullable=False)
    op.alter_column(
        "lessons", "course_id", nullable=True
    )  # Keep nullable as in original schema

    # Add primary key constraints
    op.create_primary_key("courses_pkey", "courses", ["id"])
    op.create_primary_key("lessons_pkey", "lessons", ["id"])

    # Recreate indexes
    op.create_index("ix_courses_id", "courses", ["id"], unique=False)
    op.create_index("ix_lessons_id", "lessons", ["id"], unique=False)

    # Recreate foreign key constraint
    op.create_foreign_key(
        "lessons_course_id_fkey", "lessons", "courses", ["course_id"], ["id"]
    )

    # Drop the old integer sequences since we no longer need them with UUIDs
    op.execute("DROP SEQUENCE IF EXISTS courses_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS lessons_id_seq")


def downgrade() -> None:
    """Downgrade schema."""
    # This is a destructive migration - we cannot safely downgrade from UUID to Integer
    # without losing data or creating conflicts, especially since UUIDv7 values
    # cannot be converted back to meaningful integer sequences.
    raise RuntimeError(
        "Cannot downgrade from UUID to Integer IDs. This would be destructive and "
        "could cause data loss. If you need to revert this change, you should "
        "restore from a backup taken before this migration was applied."
    )
