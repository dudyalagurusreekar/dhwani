"""
Twilio SMS Notification Provider for Dhwani / EchoShield AI
Dispatches critical security alerts to configured administrative phone numbers.
Supports:
- DHWANI_ALERT_DRY_RUN=true: Simulated logging without incurring Twilio SMS costs.
- Production SMS delivery via Twilio REST API when credentials are provided.
"""

import logging
import os
from typing import Any, Dict
import httpx
from backend.notifications.providers.base import NotificationProvider, NotificationResult

logger = logging.getLogger("dhwani.notifications.sms")


class TwilioSMSProvider(NotificationProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
        self.alert_phone = os.getenv("DHWANI_ALERT_PHONE_NUMBER", "").strip()
        self.dry_run = os.getenv("DHWANI_ALERT_DRY_RUN", "true").lower() in ("true", "1", "yes")

    @property
    def name(self) -> str:
        return "sms"

    def is_configured(self) -> bool:
        if self.dry_run:
            return True
        return bool(self.account_sid and self.auth_token and self.from_phone and self.alert_phone)

    async def send_alert(self, alert_event: Dict[str, Any]) -> NotificationResult:
        incident_id = alert_event.get("incident_id", "INCIDENT")
        risk_score = alert_event.get("risk_score", 0)
        status = alert_event.get("status", "HIGH")
        call_id = alert_event.get("call_id", "UNKNOWN")
        masked_call_id = call_id[:8] + "..." if len(call_id) > 8 else call_id

        # Strict template conforming to Requirement 10: Never include unnecessary personal data
        message_body = (
            f"DHWANI SECURITY ALERT\n"
            f"High-risk voice impersonation detected.\n"
            f"Risk: {risk_score}%\n"
            f"Call ID: {masked_call_id}\n"
            f"Status: Secondary verification required\n"
            f"Incident: {incident_id}"
        )

        if self.dry_run:
            logger.info(f"[SMS DRY RUN] Would send to {self.alert_phone or 'SIMULATED_TARGET'}:\n{message_body}")
            return NotificationResult(
                provider=self.name,
                success=True,
                message_id=f"dry_run_{incident_id}",
            )

        if not self.is_configured():
            return NotificationResult(
                provider=self.name,
                success=False,
                error="Twilio credentials (ACCOUNT_SID, AUTH_TOKEN, PHONE_NUMBER, or ALERT_PHONE) missing.",
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.from_phone,
            "To": self.alert_phone,
            "Body": message_body,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                )
                if resp.status_code in (200, 201):
                    resp_json = resp.json()
                    sid = resp_json.get("sid", "sent")
                    logger.info(f"Twilio SMS dispatched successfully. SID: {sid}")
                    return NotificationResult(
                        provider=self.name,
                        success=True,
                        message_id=sid,
                    )
                else:
                    err_msg = f"Twilio API Error {resp.status_code}: {resp.text}"
                    logger.error(err_msg)
                    return NotificationResult(
                        provider=self.name,
                        success=False,
                        error=err_msg,
                    )
        except Exception as e:
            logger.error(f"Failed to dispatch Twilio SMS: {e}")
            return NotificationResult(
                provider=self.name,
                success=False,
                error=str(e),
            )
