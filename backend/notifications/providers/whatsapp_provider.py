"""
Twilio WhatsApp Notification Provider for Dhwani / EchoShield AI
Adheres to strict verification rules: WhatsApp is ONLY enabled when explicitly configured
with a verified WhatsApp sender (e.g., whatsapp:+14155238886) and recipient.
"""

import logging
import os
from typing import Any, Dict
import httpx
from backend.notifications.providers.base import NotificationProvider, NotificationResult

logger = logging.getLogger("dhwani.notifications.whatsapp")


class TwilioWhatsAppProvider(NotificationProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
        self.whatsapp_to = os.getenv("DHWANI_WHATSAPP_ALERT_NUMBER", "").strip()
        self.enabled = os.getenv("DHWANI_WHATSAPP_ENABLED", "false").lower() in ("true", "1", "yes")

    @property
    def name(self) -> str:
        return "whatsapp"

    def is_configured(self) -> bool:
        return bool(
            self.enabled
            and self.account_sid
            and self.auth_token
            and self.whatsapp_from.startswith("whatsapp:")
            and self.whatsapp_to.startswith("whatsapp:")
        )

    async def send_alert(self, alert_event: Dict[str, Any]) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(
                provider=self.name,
                success=False,
                error="WhatsApp provider is not enabled or lacks verified whatsapp:+ sender/recipient configuration.",
            )

        incident_id = alert_event.get("incident_id", "INCIDENT")
        risk_score = alert_event.get("risk_score", 0)

        body = (
            f"*DHWANI CRITICAL ALERT*\n"
            f"Voice Cloning Impersonation Anomaly Detected.\n"
            f"Risk Level: HIGH ({risk_score}%)\n"
            f"Incident ID: `{incident_id}`\n"
            f"Mandatory Action: Secondary Verification Required."
        )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.whatsapp_from,
            "To": self.whatsapp_to,
            "Body": body,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if resp.status_code in (200, 201):
                    sid = resp.json().get("sid", "sent")
                    logger.info(f"WhatsApp alert dispatched successfully. SID: {sid}")
                    return NotificationResult(provider=self.name, success=True, message_id=sid)
                else:
                    err = f"WhatsApp delivery rejected: {resp.status_code} - {resp.text}"
                    logger.warning(err)
                    return NotificationResult(provider=self.name, success=False, error=err)
        except Exception as e:
            return NotificationResult(provider=self.name, success=False, error=str(e))
