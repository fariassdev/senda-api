"""Script serialization utilities for lesson scripts."""

import json
from typing import Any

from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import ScriptPartDTO


class LessonScript:
    """Domain utility for lesson script serialization and deserialization."""

    @staticmethod
    def serialize(script_parts: list[ScriptPartDTO]) -> str:
        """Serialize a list of ScriptPartDTO to JSON string."""
        script_data = [part.to_dict() for part in script_parts]
        return json.dumps(script_data)

    @staticmethod
    def deserialize(script_json: str | None) -> list[ScriptPartDTO] | None:
        """Deserialize JSON string to list of ScriptPartDTO."""
        if not script_json:
            return None

        try:
            script_data = json.loads(script_json)
            return [ScriptPartDTO.from_dict(part) for part in script_data]
        except (json.JSONDecodeError, KeyError, ValueError):
            # Return None for invalid script data
            return None
