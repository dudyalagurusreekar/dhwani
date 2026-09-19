"""
Audio Privacy & Data Protection Module for Dhwani.
Enforces zero-retention defaults, AES/Fernet encryption for retained recordings,
configurable retention lifecycles, and audited decryption access control.
"""

from .encryption import (
    encrypt_audio,
    decrypt_audio,
    generate_encryption_key,
    secure_wipe_buffer,
    AudioVault,
)
from .retention import (
    RetentionPolicy,
    AudioRecordMetadata,
    RetentionManager,
    get_retention_manager,
)
from .access_control import (
    AudioAccessGate,
    AudioAccessLogEntry,
    AccessDeniedError,
)

__all__ = [
    "encrypt_audio",
    "decrypt_audio",
    "generate_encryption_key",
    "secure_wipe_buffer",
    "AudioVault",
    "RetentionPolicy",
    "AudioRecordMetadata",
    "RetentionManager",
    "get_retention_manager",
    "AudioAccessGate",
    "AudioAccessLogEntry",
    "AccessDeniedError",
]
