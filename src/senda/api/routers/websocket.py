"""WebSocket router for real-time lesson and course generation updates."""

import json
import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import UUID

from src.senda.api.core.redis import RedisClient


router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
)


class ConnectionManager:
    """Manages WebSocket connections and Redis subscriptions."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

        # Remove from all subscriptions
        for channel_subs in self.subscriptions.values():
            channel_subs.discard(websocket)

    def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a WebSocket to a Redis channel."""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(websocket)

    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a WebSocket from a Redis channel."""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(websocket)

            # Clean up empty subscription sets
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]

    async def send_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast a message to all WebSockets subscribed to a channel."""
        if channel in self.subscriptions:
            disconnected = []
            for websocket in self.subscriptions[channel]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to WebSocket: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected WebSockets
            for websocket in disconnected:
                self.disconnect(websocket)


manager = ConnectionManager()


async def redis_listener():
    """Background task that listens to Redis and broadcasts to WebSockets."""
    pubsub = RedisClient.get_pubsub()

    while True:
        try:
            # Check if there are any active subscriptions
            if manager.subscriptions:
                # Subscribe to all channels that have active WebSocket subscribers
                channels = list(manager.subscriptions.keys())

                # Unsubscribe from channels no longer needed
                current_channels = (
                    set(pubsub.channels.keys())
                    if hasattr(pubsub, "channels")
                    else set()
                )
                for channel in current_channels:
                    if channel not in channels:
                        pubsub.unsubscribe(channel)

                # Subscribe to new channels
                for channel in channels:
                    if channel not in current_channels:
                        pubsub.subscribe(channel)

                # Listen for messages
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    # Broadcast to all WebSockets subscribed to this channel
                    await manager.broadcast_to_channel(channel, data)
            else:
                # No active subscriptions, just wait
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in Redis listener: {e}")
            await asyncio.sleep(1)


@router.websocket("/lessons/{lesson_id}")
async def lesson_websocket(websocket: WebSocket, lesson_id: UUID):
    """WebSocket endpoint for lesson generation updates."""
    await manager.connect(websocket)

    channel = f"lesson:{lesson_id}"
    manager.subscribe(websocket, channel)

    try:
        # Keep the connection alive and handle client messages
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong or other client messages
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"WebSocket disconnected from lesson {lesson_id}")
    except Exception as e:
        print(f"Error in lesson WebSocket: {e}")
        manager.disconnect(websocket)


@router.websocket("/courses/{course_id}")
async def course_websocket(websocket: WebSocket, course_id: UUID):
    """WebSocket endpoint for course generation updates."""
    await manager.connect(websocket)

    channel = f"course:{course_id}"
    manager.subscribe(websocket, channel)

    try:
        # Keep the connection alive and handle client messages
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong or other client messages
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"WebSocket disconnected from course {course_id}")
    except Exception as e:
        print(f"Error in course WebSocket: {e}")
        manager.disconnect(websocket)


# Start the Redis listener as a background task when the app starts
def start_redis_listener():
    """Start the Redis listener background task."""
    asyncio.create_task(redis_listener())
