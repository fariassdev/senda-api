from fastapi import APIRouter

from version import response

router = APIRouter()


@router.get("")
async def health_check() -> dict:
    """
    Health check endpoint for Cloud Run liveness and startup probes.
    Returns application status, version, and basic health information.
    """
    return response


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Readiness check endpoint for Cloud Run.
    Can be extended to check database connectivity, external services, etc.
    """
    return {"status": "ready"}
