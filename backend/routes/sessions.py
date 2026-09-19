<<<<<<< HEAD
from fastapi import APIRouter, HTTPException

from sessions.manager import SessionManager


router = APIRouter(prefix="/session")

session_manager = SessionManager()


@router.post("")
async def create_session():

    session = session_manager.create_session()

    return session


@router.get("/{session_id}")
async def get_session(session_id: str):

    session = session_manager.get_session(session_id)

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return session


@router.delete("/{session_id}")
async def close_session(session_id: str):

    success = session_manager.close_session(
        session_id
    )

    if not success:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {
        "status": "closed"
=======
from fastapi import APIRouter, HTTPException

from sessions.manager import SessionManager


router = APIRouter(prefix="/session")

session_manager = SessionManager()


@router.post("")
async def create_session():

    session = session_manager.create_session()

    return session


@router.get("/{session_id}")
async def get_session(session_id: str):

    session = session_manager.get_session(session_id)

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return session


@router.delete("/{session_id}")
async def close_session(session_id: str):

    success = session_manager.close_session(
        session_id
    )

    if not success:

        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    return {
        "status": "closed"
>>>>>>> 3b89e99 (Integrate W2V2 detection with Android and backend)
    }