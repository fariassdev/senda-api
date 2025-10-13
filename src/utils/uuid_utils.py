"""
UUID utility functions for generating UUIDv7 identifiers.
"""

import uuid
import time
from typing import Union


def generate_uuidv7() -> uuid.UUID:
    """
    Generate a UUIDv7 (time-ordered UUID).

    UUIDv7 provides better database performance compared to UUIDv4
    because it's time-ordered and reduces index fragmentation.

    Returns:
        uuid.UUID: A new UUIDv7 identifier
    """
    # Get current timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)

    # Generate random bytes for the rest
    random_bytes = uuid.uuid4().bytes

    # Create UUIDv7 structure:
    # - 48 bits: timestamp (milliseconds since epoch)
    # - 12 bits: version (7) + random
    # - 62 bits: random
    # - 2 bits: variant (10)

    # Pack timestamp into first 6 bytes
    timestamp_bytes = timestamp_ms.to_bytes(6, byteorder="big")

    # Set version to 7 (bits 12-15 of time_hi_and_version)
    version_byte = 0x70 | (random_bytes[6] & 0x0F)

    # Set variant bits (bits 6-7 of clock_seq_hi_and_reserved)
    variant_byte = 0x80 | (random_bytes[8] & 0x3F)

    # Combine all bytes (total 16 bytes)
    uuid_bytes = (
        timestamp_bytes  # 6 bytes: timestamp
        + bytes([version_byte])  # 1 byte: version + random
        + bytes([random_bytes[7]])  # 1 byte: random
        + bytes([variant_byte])  # 1 byte: variant + random
        + random_bytes[9:16]  # 7 bytes: random
    )

    return uuid.UUID(bytes=uuid_bytes)


def uuid_from_string(uuid_str: Union[str, uuid.UUID]) -> uuid.UUID:
    """
    Convert a string or UUID to UUID object.

    Args:
        uuid_str: String representation of UUID or UUID object

    Returns:
        uuid.UUID: UUID object

    Raises:
        ValueError: If the string is not a valid UUID
    """
    if isinstance(uuid_str, uuid.UUID):
        return uuid_str

    try:
        return uuid.UUID(uuid_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid UUID string: {uuid_str}") from e


def uuid_to_string(uuid_obj: Union[str, uuid.UUID]) -> str:
    """
    Convert UUID object to string representation.

    Args:
        uuid_obj: UUID object or string

    Returns:
        str: String representation of the UUID
    """
    if isinstance(uuid_obj, str):
        # Validate it's a proper UUID string
        uuid.UUID(uuid_obj)
        return uuid_obj

    return str(uuid_obj)
