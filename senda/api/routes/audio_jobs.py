from uuid import UUID

from fastapi import APIRouter, Path

from senda.api.schemas.responses.audio_generation import (
    AudioGenerationJobStatusResponse,
)
from senda.core.dependencies import (
    AuthenticatedUser,
    DBSession,
    IAudioGenerationService,
)

router = APIRouter()


@router.get("/{job_id}/status", response_model=AudioGenerationJobStatusResponse)
async def get_audio_generation_job_status(
    session: DBSession,
    current_user: AuthenticatedUser,
    audio_service: IAudioGenerationService,
    job_id: UUID = Path(..., description="Audio generation job ID"),
) -> AudioGenerationJobStatusResponse:
    """Poll operational status for an HLS audio generation job."""
    status_dto = await audio_service.get_job_status(session=session, job_id=job_id)
    return AudioGenerationJobStatusResponse.from_dto(status_dto)
