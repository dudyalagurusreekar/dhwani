"""
Dhwani / EchoShield - Audit Ledger API Routes
Provides REST endpoints for querying, verifying, and exporting the tamper-evident hash chain.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from security import get_global_pipeline

router = APIRouter(prefix="/audit", tags=["Security & Audit"])


@router.get("/verify")
def verify_audit_chain() -> Dict[str, Any]:
    """Verify cryptographic integrity of the entire audit chain."""
    pipeline = get_global_pipeline()
    report = pipeline.chain.verify_integrity()
    return report.to_dict()


@router.get("/trail")
def get_audit_trail(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: Optional[int] = Query(100, description="Max number of events to return"),
) -> List[Dict[str, Any]]:
    """Return sequence of audited security events."""
    pipeline = get_global_pipeline()
    events = pipeline.chain.get_events(session_id=session_id, event_type=event_type, limit=limit)
    return [e.to_dict() for e in events]


@router.get("/latest")
def get_latest_hash() -> Dict[str, Any]:
    """Return the current tip hash and length of the audit chain."""
    pipeline = get_global_pipeline()
    return {
        "length": pipeline.chain.length,
        "latest_hash": pipeline.chain.latest_hash,
    }


@router.get("/certificate")
def get_verification_certificate() -> Dict[str, Any]:
    """Export sealed cryptographic verification certificate for compliance."""
    pipeline = get_global_pipeline()
    return pipeline.chain.export_verification_certificate()


@router.get("/session/{session_id}/summary")
def get_session_summary(session_id: str) -> Dict[str, Any]:
    """Return forensic summary for a specific call/stream session."""
    pipeline = get_global_pipeline()
    summary = pipeline.chain.get_session_audit_summary(session_id)
    if not summary.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"No audit records found for session {session_id}",
        )
    return summary
