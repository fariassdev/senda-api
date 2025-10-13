"""Event publisher for lesson generation status updates."""

import json
from typing import Any, Dict
from uuid import UUID
from enum import Enum
from datetime import datetime

from src.senda.api.core.redis import get_redis_client


class EventType(str, Enum):
    """Event types for lesson generation."""

    SCRIPT_STARTED = "script_started"
    SCRIPT_PROGRESS = "script_progress"
    SCRIPT_COMPLETED = "script_completed"
    SCRIPT_FAILED = "script_failed"

    AUDIO_STARTED = "audio_started"
    AUDIO_PROGRESS = "audio_progress"
    AUDIO_COMPLETED = "audio_completed"
    AUDIO_FAILED = "audio_failed"


class EventPublisher:
    """Publisher for lesson and course generation events."""

    @staticmethod
    def _get_channel(resource_type: str, resource_id: UUID) -> str:
        """Get the Redis channel name for a resource."""
        return f"{resource_type}:{resource_id}"

    @staticmethod
    def _publish_event(channel: str, event_type: EventType, data: Dict[str, Any]):
        """Publish an event to Redis."""
        try:
            redis_client = get_redis_client()
            message = {
                "event": event_type.value,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
            redis_client.publish(channel, json.dumps(message))
        except Exception as e:
            print(f"Failed to publish event to {channel}: {e}")

    # Lesson Script Events
    @staticmethod
    def publish_lesson_script_started(lesson_id: UUID):
        """Publish event when lesson script generation starts."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        EventPublisher._publish_event(
            channel,
            EventType.SCRIPT_STARTED,
            {"lesson_id": str(lesson_id), "status": "script_generating"},
        )

    @staticmethod
    def publish_lesson_script_completed(lesson_id: UUID, script_data: Any = None):
        """Publish event when lesson script generation completes."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        data = {"lesson_id": str(lesson_id), "status": "script_completed"}
        if script_data:
            data["script_preview"] = str(script_data)[:100] + "..."
        EventPublisher._publish_event(channel, EventType.SCRIPT_COMPLETED, data)

    @staticmethod
    def publish_lesson_script_failed(lesson_id: UUID, error: str):
        """Publish event when lesson script generation fails."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        EventPublisher._publish_event(
            channel,
            EventType.SCRIPT_FAILED,
            {"lesson_id": str(lesson_id), "status": "script_failed", "error": error},
        )

    # Lesson Audio Events
    @staticmethod
    def publish_lesson_audio_started(lesson_id: UUID):
        """Publish event when lesson audio generation starts."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        EventPublisher._publish_event(
            channel,
            EventType.AUDIO_STARTED,
            {"lesson_id": str(lesson_id), "status": "audio_generating"},
        )

    @staticmethod
    def publish_lesson_audio_completed(lesson_id: UUID, audio_url: str):
        """Publish event when lesson audio generation completes."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        EventPublisher._publish_event(
            channel,
            EventType.AUDIO_COMPLETED,
            {
                "lesson_id": str(lesson_id),
                "status": "audio_completed",
                "audio_url": audio_url,
            },
        )

    @staticmethod
    def publish_lesson_audio_failed(lesson_id: UUID, error: str):
        """Publish event when lesson audio generation fails."""
        channel = EventPublisher._get_channel("lesson", lesson_id)
        EventPublisher._publish_event(
            channel,
            EventType.AUDIO_FAILED,
            {"lesson_id": str(lesson_id), "status": "audio_failed", "error": error},
        )
