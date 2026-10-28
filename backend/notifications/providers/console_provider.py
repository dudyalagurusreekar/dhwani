"""
Console & Dashboard Notification Provider
Always available; logs formatted security alerts and dispatches via WebSocket.
"""

import logging
from typing import Any, Dict
from backend.notifications.providers.base import NotificationProvider, NotificationResult

logger = logging.getLogger("dhwani.notifications.console")


class ConsoleNotificationProvider(NotificationProvider):
    @property
    def name(self) -> str:
        return "console"

    def is_configured(self) -> bool:
        return True

    async def send_alert(self, alert_event: Dict[str, Any]) -> NotificationResult:
        incident_id = alert_event.get("incident_id", "UNKNOWN")
        risk_score = alert_event.get("risk_score", 0)
        risk_level = alert_event.get("risk_level", "UNKNOWN")
        source = alert_event.get("source", "telephony")

        msg = (
            f"[DHWANI SECURITY ALERT] Incident: {incident_id} | Risk: {risk_score}% ({risk_level}) | "
            f"Source: {source} | Status: Action Required"
        )
        logger.warning(msg)
        return NotificationResult(
            provider=self.name,
            success=True,
            message_id=f"console_{incident_id}",
        )
