"""
Security Incidents & Tamper-Evident Evidence Routes for Dhwani / EchoShield AI
Maintains immutable audit records, cryptographic SHA-256 hash chains,
and human-in-the-loop secondary verification workflows.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from security.audit_chain import AuditHashChain
from security.schemas import EventType
from backend.websocket.dashboard import broadcast_event

router = APIRouter(prefix="/incidents", tags=["Security Incidents & Evidence"])

# Ledger persisted to data/audit_ledger.jsonl
LEDGER_PATH = Path("data") / "audit_ledger.jsonl"
LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
audit_chain = AuditHashChain(persistence_file=LEDGER_PATH)

# In-memory incident registry
INCIDENT_RECORDS: Dict[str, Dict[str, Any]] = {}


class VerificationRequest(BaseModel):
    status: str  # "PASSED" | "FAILED" | "MANUAL_BYPASS"
    verifier_id: str = "security_analyst"
    notes: Optional[str] = None


@router.get("")
async def list_incidents():
    """
    List all recorded voice impersonation incidents with tamper-evident chain hashes.
    """
    # Verify cryptographic integrity of the chain
    chain_report = audit_chain.verify_integrity()

    incidents_list = list(INCIDENT_RECORDS.values())
    incidents_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "count": len(incidents_list),
        "chain_length": audit_chain.length,
        "chain_intact": chain_report.is_valid,
        "latest_chain_hash": audit_chain.latest_hash,
        "incidents": incidents_list,
    }


@router.get("/verify/chain")
async def verify_audit_chain():
    """
    Verify complete cryptographic SHA-256 hash integrity across the ledger.
    """
    report = audit_chain.verify_integrity()
    return {
        "is_valid": report.is_valid,
        "total_events": report.total_events,
        "tampered_index": report.tampered_event_seq,
        "error_message": report.error_reason,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """
    Retrieve single incident evidence details and cryptographic proof.
    """
    if incident_id not in INCIDENT_RECORDS:
        raise HTTPException(status_code=404, detail="Incident not found")
    return INCIDENT_RECORDS[incident_id]


@router.post("/verification/{incident_id}")
async def record_verification_result(incident_id: str, req: VerificationRequest):
    """
    Submit secondary step-up verification result (e.g. caller passed honeypot or out-of-band auth).
    """
    if incident_id not in INCIDENT_RECORDS:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENT_RECORDS[incident_id]
    incident["verification_status"] = req.status
    incident["verifier"] = req.verifier_id
    incident["verification_notes"] = req.notes
    incident["verified_at"] = datetime.now(timezone.utc).isoformat()

    # Append immutable event to hash chain
    event = audit_chain.append_event(
        session_id=incident.get("session_id", "session_unknown"),
        event_type=EventType.VERIFICATION_STEP,
        payload={
            "incident_id": incident_id,
            "verification_status": req.status,
            "verifier": req.verifier_id,
            "notes": req.notes,
        },
    )

    incident["chain_hash"] = event.chain_hash

    # Broadcast update to dashboard
    await broadcast_event("verification_updated", incident)

    return {
        "status": "SUCCESS",
        "incident_id": incident_id,
        "verification_status": req.status,
        "chain_hash": event.chain_hash,
    }


def record_security_incident(
    session_id: str,
    analysis_id: str,
    risk_score: int,
    risk_level: str,
    attack_vector: str,
    consensus: str,
    audio_hash: Optional[str] = None,
    action_taken: str = "FLAG_SUSPICIOUS",
) -> Dict[str, Any]:
    """
    Helper to record a high-risk event, bind to audit hash chain, and cache.
    """
    incident_id = f"inc_{uuid.uuid4().hex[:12]}"
    prev_hash = audit_chain.latest_hash

    event = audit_chain.append_event(
        session_id=session_id,
        event_type=EventType.RISK_ASSESSMENT,
        audio_hash=audio_hash,
        payload={
            "incident_id": incident_id,
            "analysis_id": analysis_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "attack_vector": attack_vector,
            "consensus": consensus,
            "action_taken": action_taken,
        },
    )

    record = {
        "incident_id": incident_id,
        "session_id": session_id,
        "analysis_id": analysis_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "attack_vector": attack_vector,
        "consensus": consensus,
        "action_taken": action_taken,
        "verification_status": "PENDING",
        "audio_hash": audio_hash or "REDACTED",
        "previous_hash": prev_hash,
        "current_hash": event.chain_hash,
    }

    INCIDENT_RECORDS[incident_id] = record
    return record
