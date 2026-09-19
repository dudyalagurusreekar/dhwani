<<<<<<< HEAD
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "echoshield-backend"
=======
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "echoshield-backend"
>>>>>>> 3b89e99 (Integrate W2V2 detection with Android and backend)
    }