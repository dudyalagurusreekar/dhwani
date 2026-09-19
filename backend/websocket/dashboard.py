"""
Dashboard WebSocket Broadcaster for Dhwani / EchoShield AI
Maintains active connections from frontend clients and broadcasts real-time
telemetry, call events, VAD status, risk updates, and security alerts.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("dhwani.dashboard")


class DashboardConnectionManager:
    """Manages connected browser dashboard clients and dispatches events."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"Dashboard client connected. Active clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"Dashboard client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """
        Broadcast structured JSON event to all connected dashboard clients.
        """
        payload = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        text_data = json.dumps(payload)

        async with self._lock:
            connections = list(self.active_connections)

        for ws in connections:
            try:
                await ws.send_text(text_data)
            except Exception as e:
                logger.warning(f"Error sending to dashboard client: {e}")
                async with self._lock:
                    self.active_connections.discard(ws)


# Global singleton instance
dashboard_manager = DashboardConnectionManager()


async def broadcast_event(event_type: str, data: Dict[str, Any]):
    """Convenience helper to broadcast an event globally."""
    await dashboard_manager.broadcast(event_type, data)
