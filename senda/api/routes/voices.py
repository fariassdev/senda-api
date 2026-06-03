from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from senda.api.schemas.requests.voice import CreateVoiceRequest, UpdateVoiceRequest
from senda.api.schemas.responses.voice import VoiceResponse
from senda.core.dependencies import AdminUser, DBSession, IVoiceService

router = APIRouter(prefix="/voices", tags=["Voices"])


@router.post("", response_model=VoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_voice(
    session: DBSession,
    current_user: AdminUser,
    voice_service: IVoiceService,
    reference_wav: UploadFile = File(...),
    payload: CreateVoiceRequest = Depends(CreateVoiceRequest.as_form),
) -> VoiceResponse:
    """Create a voice in the catalog with a reference WAV file.

    **Pipeline order:** Modal volume sync → TTS sample → S3 reference → S3 sample → DB insert.

    **On success:** ``201`` with the new voice; the row exists only after all steps succeed.

    **On failure:** No catalog row is created. Modal/S3 may hold data keyed by ``slug``;
    retries with the same slug overwrite those objects (see ``voice_provisioning`` module).

    **Errors:** ``409`` if the slug already exists; ``502`` if Modal or S3 fails.
    """
    wav_bytes = await reference_wav.read()

    create_dto = payload.to_dto()

    voice_dto = await voice_service.create_voice(
        session=session,
        create_item=create_dto,
        reference_wav=wav_bytes,
        current_user=current_user,
    )

    return VoiceResponse.from_dto(voice_dto)


@router.get("/{voice_slug}", response_model=VoiceResponse)
async def get_voice(
    voice_slug: str,
    session: DBSession,
    current_user: AdminUser,
    voice_service: IVoiceService,
) -> VoiceResponse:
    """Retrieve details of a specific voice by slug.

    Only accessible by administrators.
    """
    voice_dto = await voice_service.get_voice_by_slug(
        session=session, slug=voice_slug, current_user=current_user
    )
    return VoiceResponse.from_dto(voice_dto)


@router.get("", response_model=list[VoiceResponse])
async def list_voices(
    session: DBSession,
    current_user: AdminUser,
    voice_service: IVoiceService,
    active_only: bool = True,
) -> list[VoiceResponse]:
    """List available cataloged voices.

    Only accessible by administrators.
    """
    voices = await voice_service.list_voices(
        session=session, active_only=active_only, current_user=current_user
    )
    return [VoiceResponse.from_dto(v) for v in voices]


@router.put("/{voice_id}", response_model=VoiceResponse)
async def update_voice(
    voice_id: UUID,
    payload: UpdateVoiceRequest,
    session: DBSession,
    current_user: AdminUser,
    voice_service: IVoiceService,
) -> VoiceResponse:
    """Update settings of an existing voice.

    Only accessible by administrators.
    """
    update_dto = payload.to_dto()

    voice_dto = await voice_service.update_voice(
        session=session,
        voice_id=voice_id,
        update_item=update_dto,
        current_user=current_user,
    )

    return VoiceResponse.from_dto(voice_dto)
