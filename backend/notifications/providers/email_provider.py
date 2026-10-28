"""
Email Notification Fallback Provider for Dhwani / EchoShield AI
Dispatches incident notifications via SMTP when higher-priority channels fail or as a backup.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Any, Dict
from backend.notifications.providers.base import NotificationProvider, NotificationResult

logger = logging.getLogger("dhwani.notifications.email")


class EmailNotificationProvider(NotificationProvider):
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "").strip()
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "").strip()
        self.password = os.getenv("SMTP_PASSWORD", "").strip()
        self.to_email = os.getenv("DHWANI_ALERT_EMAIL", "").strip()
        self.from_email = os.getenv("DHWANI_FROM_EMAIL", self.user or "alerts@dhwani.ai").strip()

    @property
    def name(self) -> str:
        return "email"

    def is_configured(self) -> bool:
        return bool(self.host and self.to_email)

    def _send_sync(self, subject: str, body_text: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = self.to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.port in (587, 25):
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)

    async def send_alert(self, alert_event: Dict[str, Any]) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(
                provider=self.name,
                success=False,
                error="Email provider unconfigured (SMTP_HOST or DHWANI_ALERT_EMAIL missing).",
            )

        incident_id = alert_event.get("incident_id", "UNKNOWN")
        risk_score = alert_event.get("risk_score", 0)
        subject = f"[DHWANI CRITICAL ALERT] Impersonation Risk: {risk_score}%"
        body = (
            f"Dhwani Cybersecurity Notification\n"
            f"===================================\n"
            f"Incident ID: {incident_id}\n"
            f"Risk Score:  {risk_score}%\n"
            f"Risk Level:  {alert_event.get('risk_level', 'HIGH')}\n"
            f"Timestamp:   {alert_event.get('timestamp')}\n"
            f"Attribution: {alert_event.get('attack_vector', 'UNKNOWN')}\n"
            f"Action:      {alert_event.get('policy_action', 'HOLD_PROTECTED_ACTION')}\n\n"
            f"Please verify caller credentials via secondary channel."
        )

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._send_sync, subject, body)
            logger.info(f"Email alert sent to {self.to_email}")
            return NotificationResult(
                provider=self.name,
                success=True,
                message_id=f"email_{incident_id}",
            )
        except Exception as e:
            logger.warning(f"Email alert failed: {e}")
            return NotificationResult(
                provider=self.name,
                success=False,
                error=str(e),
            )
