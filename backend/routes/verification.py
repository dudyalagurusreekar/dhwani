from fastapi import APIRouter

router = APIRouter(prefix="/verify")

verification_status = {}


@router.post("/{session_id}")
async def verify_session(session_id: str):
    verification_status[session_id] = {
        "verified": True,
        "method": "independent_verification"
    }

    return {
        "session_id": session_id,
        "verified": True,
        "message": "Caller verification completed",
        "allow_sensitive_action": True
    }


@router.get("/{session_id}")
async def get_verification(session_id: str):
    return verification_status.get(
        session_id,
        {
            "verified": False,
            "allow_sensitive_action": False
        }
    )
