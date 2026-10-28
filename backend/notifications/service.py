"""
Notification Service for Dhwani / EchoShield AI
Manages multi-channel priority dispatch (SMS -> WhatsApp -> Email -> Dashboard),
enforces temporal confirmation, rate-limiting, and cooldown deduplication.
"""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set

from backend.notifications.providers.base import NotificationProvider, NotificationResult
from backend.notifications.providers.console_provider import ConsoleNotificationProvider
from backend.notifications.providers.twilio_sms_provider import TwilioSMSProvider
from backend.notifications.providers.whatsapp_provider import TwilioWhatsAppProvider
from backend.notifications.providers.email_provider import EmailNotificationProvider
from backend.websocket.dashboard import broadcast_event

logger = logging.getLogger("dhwani.notifications")


class NotificationService:
    """
    Central alert dispatch coordinator with fallback routing and spam prevention.
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self.sms_provider = TwilioSMSProvider()
        self.whatsapp_provider = TwilioWhatsAppProvider()
        self.email_provider = EmailNotificationProvider()
        self.console_provider = ConsoleNotificationProvider()

        # Deduplication & rate-limiting cache
        self._last_alert_time: Dict[str, float] = {}  # session_id -> timestamp
        self._alerted_incidents: Set[str] = set()

    def can_alert(self, session_id: str, incident_id: Optional[str] = None) -> bool:
        """Check if an alert is permitted under cooldown and deduplication policies."""
        if incident_id and incident_id in self._alerted_incidents:
            return False

        last_time = self._last_alert_time.get(session_id, 0.0)
        now = time.time()
        if now - last_time < self.cooldown_seconds:
            return False

        return True

    async def dispatch_security_alert(self, alert_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute fallback notification chain:
        1. SMS (Primary if configured)
        2. WhatsApp (Fallback if SMS fails and WhatsApp is supported/configured)
        3. Email (Tertiary fallback)
        4. Dashboard Broadcast (Always executed)
        """
        session_id = alert_event.get("call_id") or alert_event.get("session_id") or "global"
        incident_id = alert_event.get("incident_id")

        if not self.can_alert(session_id, incident_id):
            logger.info(f"Alert suppressed by cooldown/deduplication policy for session: {session_id}")
            return {
                "notification_status": "SUPPRESSED",
                "reason": "Cooldown active or duplicate incident",
                "providers": [],
            }

        now = time.time()
        self._last_alert_time[session_id] = now
        if incident_id:
            self._alerted_incidents.add(incident_id)

        results: List[Dict[str, Any]] = []
        any_external_sent = False

        # 1. Primary: SMS
        if self.sms_provider.is_configured():
            sms_res = await self.sms_provider.send_alert(alert_event)
            results.append({"provider": "sms", "status": "sent" if sms_res.success else "failed", "error": sms_res.error})
            if sms_res.success:
                any_external_sent = True

        # 2. Secondary Fallback: WhatsApp (only if SMS was unconfigured or failed)
        if not any_external_sent and self.whatsapp_provider.is_configured():
            wa_res = await self.whatsapp_provider.send_alert(alert_event)
            results.append({"provider": "whatsapp", "status": "sent" if wa_res.success else "failed", "error": wa_res.error})
            if wa_res.success:
                any_external_sent = True

        # 3. Tertiary Fallback: Email (if prior external methods failed/unconfigured)
        if not any_external_sent and self.email_provider.is_configured():
            email_res = await self.email_provider.send_alert(alert_event)
            results.append({"provider": "email", "status": "sent" if email_res.success else "failed", "error": email_res.error})
            if email_res.success:
                any_external_sent = True

        # 4. Mandatory: Console & Dashboard Alert
        console_res = await self.console_provider.send_alert(alert_event)
        results.append({"provider": "dashboard", "status": "sent" if console_res.success else "failed"})

        # Dispatch real-time dashboard notification
        await broadcast_event("security_alert", alert_event)

        final_status = "SENT" if any_external_sent else "DASHBOARD_ONLY"
        return {
            "notification_status": final_status,
            "providers": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global singleton instance
notification_service = NotificationService()
