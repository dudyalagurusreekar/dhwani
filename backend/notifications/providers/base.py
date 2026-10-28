"""
Base Provider Interface for Dhwani Notifications
Standardizes notification dispatch results across SMS, WhatsApp, Email, and Console channels.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class NotificationResult:
    provider: str
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class NotificationProvider(ABC):
    """Abstract interface for a notification channel."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'sms', 'whatsapp', 'email', 'console')."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if credentials and destination are validly configured."""
        pass

    @abstractmethod
    async def send_alert(self, alert_event: Dict[str, Any]) -> NotificationResult:
        """Dispatch notification and return structured result."""
        pass
