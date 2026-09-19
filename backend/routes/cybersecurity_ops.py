"""
EchoShield AI - Cybersecurity Operations Router.

Exposes endpoints for:
1. API Security: JWT Token Issuance & Verification
2. Digital Signatures: Ed25519 Checkpoint Signing & Public-Key Verification
3. Audio Privacy: Encrypted Retention Management & Controlled Decryption
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cybersecurity.api_security.authentication import (
    create_access_token,
    get_current_user,
)
from cybersecurity.api_security.authorization import (
    Permission,
    Role,
    require_permission,
    require_role,
)
from cybersecurity.audit_verification.checkpoint import (
    AuditCheckpoint,
    create_checkpoint,
)
from cybersecurity.audit_verification.signatures import (
    AuditSigner,
    export_public_key_pem,
)
from cybersecurity.audit_verification.verify_signature import (
    verify_checkpoint_integrity,
)
from cybersecurity.audio_privacy.access_control import (
    AccessDeniedError,
    AudioAccessGate,
)
from cybersecurity.audio_privacy.retention import (
    RetentionPolicy,
    get_retention_manager,
)
from security import get_global_pipeline

router = APIRouter(prefix="/security", tags=["Cybersecurity Operations"])

# Global audit signer instance (holding private key in validator enclave)
_global_signer = AuditSigner(signer_id="dhwani-validator-node-01")
_global_access_gate = AudioAccessGate(
    retention_manager=get_retention_manager(),
    audit_chain=get_global_pipeline().chain,
)


class TokenRequest(BaseModel):
    subject: str = Field(..., example="agent_node_101")
    role: str = Field("client", example="client")
    scopes: Optional[List[str]] = Field(default_factory=list, example=["audio:analyze"])
    expires_minutes: Optional[int] = Field(60, example=60)


class CheckpointVerifyRequest(BaseModel):
    checkpoint: Dict[str, Any]
    trusted_public_key_pem: Optional[str] = None


class AudioDecryptRequest(BaseModel):
    record_id: str
    justification: str


@router.post("/token", summary="Issue cryptographically signed JWT access token")
async def issue_token(req: TokenRequest):
    """
    Issues a JWT token with embedded RBAC role and permission scopes.
    Supported roles: client, analyst, auditor, admin.
    """
    token = create_access_token(
        subject=req.subject,
        role=req.role,
        scopes=req.scopes,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": req.role,
        "subject": req.subject,
    }


@router.get("/validator/public-key", summary="Get Ed25519 validator public key (PEM)")
async def get_validator_public_key():
    """Returns the validator public key used for audit checkpoint verification."""
    return {
        "signer_id": _global_signer.signer_id,
        "algorithm": "Ed25519",
        "public_key_pem": _global_signer.public_key_pem,
        "public_key_hex": _global_signer.public_key_hex,
    }


@router.post("/checkpoint/sign", summary="Sign current audit chain tip with Ed25519")
async def sign_audit_checkpoint(user: Dict[str, Any] = Depends(require_role(Role.AUDITOR, Role.ADMIN))):
    """
    Digitally signs the latest tip of the audit hash chain using an Ed25519 private key.
    Requires AUDITOR or ADMIN role.
    """
    pipeline = get_global_pipeline()
    checkpoint = create_checkpoint(pipeline.chain, _global_signer)
    return JSONResponse(content=checkpoint.to_dict())


@router.post("/checkpoint/verify", summary="Verify signed audit checkpoint and detect history rewriting")
async def verify_checkpoint(req: CheckpointVerifyRequest):
    """
    Validates the Ed25519 signature of an audit checkpoint and confirms whether
    the signed tip matches the current audit hash chain.
    """
    pipeline = get_global_pipeline()
    try:
        chk = AuditCheckpoint.from_dict(req.checkpoint)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Malformed checkpoint: {str(exc)}")

    result = verify_checkpoint_integrity(
        checkpoint=chk,
        chain=pipeline.chain,
        trusted_public_key_pem=req.trusted_public_key_pem or _global_signer.public_key_pem,
    )

    status_code = 200 if result.is_valid else 409
    return JSONResponse(status_code=status_code, content=result.to_dict())


@router.get("/retention/records", summary="List active retained audio records")
async def list_retention_records(user: Dict[str, Any] = Depends(require_role(Role.AUDITOR, Role.ADMIN))):
    """Lists non-purged retained audio recordings. Requires AUDITOR or ADMIN role."""
    mgr = get_retention_manager()
    records = mgr.list_active_records()
    return [r.to_dict() for r in records]


@router.post("/retention/purge", summary="Manually trigger expired audio purging")
async def purge_expired_audio(user: Dict[str, Any] = Depends(require_role(Role.ADMIN))):
    """Shreds and securely removes audio recordings whose TTL has elapsed."""
    mgr = get_retention_manager()
    purged_ids = mgr.purge_expired_records()
    return {"purged_count": len(purged_ids), "purged_record_ids": purged_ids}


@router.post("/audio/decrypt", summary="Request controlled decryption of retained audio")
async def decrypt_audio_recording(
    req: AudioDecryptRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Authorizes decryption of encrypted audio, logs forensic justification,
    and returns hex-encoded audio payload.
    Requires AUDIO_DECRYPT permission.
    """
    try:
        decrypted_bytes = _global_access_gate.request_audio_decryption(
            record_id=req.record_id,
            user=user,
            justification=req.justification,
        )
        return {
            "record_id": req.record_id,
            "size_bytes": len(decrypted_bytes),
            "audio_hex": decrypted_bytes.hex(),
        }
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
