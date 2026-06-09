from fastapi import APIRouter, BackgroundTasks, Path
from starlette import status

from senda.api.schemas.requests.lesson import (
    BatchAudioGenerationRequest,
    BatchScriptGenerationRequest,
    CreateLessonRequest,
    ReorderLessonsRequest,
    SingleAudioGenerationRequest,
    UpdateLessonRequest,
)
from senda.api.schemas.responses.audio_generation import (
    AudioGenerationResponse,
    AudioGenerationStatusResponse,
    CourseAudiosGenerationResponse,
    StartAudioGenerationResponse,
)
from senda.api.schemas.responses.lesson import LessonResponse, LessonsListResponse
from senda.api.schemas.responses.script_generation import (
    CourseScriptsGenerationResponse,
    ScriptGenerationStatusResponse,
)
from senda.core.dependencies import (
    AdminUser,
    AuthenticatedUser,
    DBSession,
    IAudioGenerationService,
    ILessonService,
    IScriptGenerationService,
    OptionalUser,
)
from senda.core.enums import LessonStatus
from senda.domain.dtos.audio_generation import (
    AudioConfigDTO,
    AudioGenerationRequestDTO,
    CourseAudioGenerationRequestDTO,
)
from senda.domain.dtos.script_generation import CourseScriptRequestDTO

router = APIRouter()


@router.get("/{slug}/lessons", response_model=LessonsListResponse)
async def get_lessons(
    slug: str,
    session: DBSession,
    current_user: OptionalUser,
    lesson_service: ILessonService,
) -> LessonsListResponse:
    """
    Get lessons for a course.
    """
    lesson_list_dto = await lesson_service.get_course_lessons(
        session=session, slug=slug, current_user=current_user
    )
    return LessonsListResponse.from_dto(dto=lesson_list_dto)


@router.get("/{slug}/lessons/{id}", response_model=LessonResponse)
async def get_lesson(
    slug: str,
    session: DBSession,
    current_user: OptionalUser,
    lesson_service: ILessonService,
    lesson_id: int = Path(..., alias="id"),
) -> LessonResponse:
    """
    Get a specific lesson for a course.
    """
    lesson_dto = await lesson_service.get_course_lesson(
        session=session, slug=slug, lesson_id=lesson_id, current_user=current_user
    )
    return LessonResponse.from_dto(dto=lesson_dto)


@router.post(
    "/{slug}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    slug: str,
    payload: CreateLessonRequest,
    session: DBSession,
    current_user: AuthenticatedUser,
    lesson_service: ILessonService,
) -> LessonResponse:
    """
    Create a lesson for a course.
    """
    lesson_dto = await lesson_service.create_course_lesson(
        session=session,
        slug=slug,
        lesson_to_create=payload.to_dto(),
        current_user=current_user,
    )
    return LessonResponse.from_dto(dto=lesson_dto)


@router.put("/{slug}/lessons/{id}", response_model=LessonResponse)
async def update_lesson(
    slug: str,
    payload: UpdateLessonRequest,
    session: DBSession,
    current_user: AdminUser,
    lesson_service: ILessonService,
    lesson_id: int = Path(..., alias="id"),
) -> LessonResponse:
    """
    Update a lesson for a course.
    """
    lesson_dto = await lesson_service.update_course_lesson(
        session=session,
        slug=slug,
        lesson_id=lesson_id,
        lesson_to_update=payload.to_dto(),
        current_user=current_user,
    )
    return LessonResponse.from_dto(dto=lesson_dto)


@router.delete("/{slug}/lessons/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    slug: str,
    session: DBSession,
    current_user: AdminUser,
    lesson_service: ILessonService,
    lesson_id: int = Path(..., alias="id"),
) -> None:
    """
    Delete a lesson for a course.
    """
    await lesson_service.delete_course_lesson(
        session=session, slug=slug, lesson_id=lesson_id, current_user=current_user
    )


@router.patch("/{slug}/lessons/reorder", response_model=LessonsListResponse)
async def reorder_lessons(
    slug: str,
    payload: ReorderLessonsRequest,
    session: DBSession,
    current_user: AdminUser,
    lesson_service: ILessonService,
) -> LessonsListResponse:
    """
    Reorder lessons for a course.
    """
    lesson_list_dto = await lesson_service.reorder_course_lessons(
        session=session,
        slug=slug,
        reorder_data=payload.to_dto(),
        current_user=current_user,
    )
    return LessonsListResponse.from_dto(dto=lesson_list_dto)


# Script Generation Endpoints


@router.post(
    "/{slug}/lessons/{id}/generate-script",
    response_model=ScriptGenerationStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_lesson_script(
    slug: str,
    session: DBSession,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    script_service: IScriptGenerationService,
    lesson_id: int = Path(..., alias="id"),
) -> ScriptGenerationStatusResponse:
    """
    Generate script for a specific lesson asynchronously.
    """
    start_result = await script_service.start_script_generation(
        session=session, lesson_id=lesson_id
    )

    if start_result.is_new:
        background_tasks.add_task(
            script_service.run_script_generation, lesson_id, current_user.id
        )

    return ScriptGenerationStatusResponse(
        lesson_id=start_result.lesson_id, status=start_result.status
    )


@router.post(
    "/{slug}/generate-batch-scripts",
    response_model=CourseScriptsGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_course_scripts(
    slug: str,
    payload: BatchScriptGenerationRequest,
    session: DBSession,
    current_user: AdminUser,
    script_service: IScriptGenerationService,
) -> CourseScriptsGenerationResponse:
    """
    Generate scripts for specific lessons in a course.

    - If lesson_ids is not provided: generates for all eligible lessons
    - If lesson_ids is []: generates nothing
    - If lesson_ids is [1, 2, 3]: generates only for those specific lessons

    Returns successful generations and any errors that occurred.
    """
    request = CourseScriptRequestDTO(
        user_id=current_user.id, slug=slug, lesson_ids=payload.lesson_ids
    )

    batch_result = await script_service.generate_course_scripts(
        session=session, request=request
    )

    return CourseScriptsGenerationResponse.from_batch_result(batch_result)


@router.get(
    "/{slug}/lessons/{id}/script-status", response_model=ScriptGenerationStatusResponse
)
async def get_lesson_script_status(
    slug: str,
    session: DBSession,
    current_user: AuthenticatedUser,
    script_service: IScriptGenerationService,
    lesson_id: int = Path(..., alias="id"),
) -> ScriptGenerationStatusResponse:
    """
    Get the current script generation status for a lesson.
    """
    status_value = await script_service.get_lesson_generation_status(
        session=session, lesson_id=lesson_id, user_id=current_user.id
    )

    return ScriptGenerationStatusResponse(lesson_id=lesson_id, status=status_value)


@router.post(
    "/{slug}/lessons/{id}/generate-audio",
    response_model=StartAudioGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_lesson_audio(
    slug: str,
    session: DBSession,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    audio_service: IAudioGenerationService,
    payload: SingleAudioGenerationRequest,
    lesson_id: int = Path(..., alias="id"),
) -> StartAudioGenerationResponse:
    """
    Start async HLS audio generation for a specific lesson.

    Returns immediately with a job id and live playlist URL. Poll
    ``GET /api/jobs/{job_id}/status`` for segment progress.

    Requires ``audio_config.voice_id`` referencing an active catalog voice.
    """
    audio_config = AudioConfigDTO(
        voice_id=payload.audio_config.voice_id,
        speed=payload.audio_config.resolved_speed(),
    )

    request = AudioGenerationRequestDTO(
        lesson_id=lesson_id, user_id=current_user.id, audio_config=audio_config
    )

    start_result = await audio_service.start_generation_job(
        session=session, request=request
    )

    if start_result.is_new:
        background_tasks.add_task(
            audio_service.run_generation_pipeline, start_result.job_id
        )

    return StartAudioGenerationResponse.from_dto(start_result)


@router.post(
    "/{slug}/generate-batch-audios",
    response_model=CourseAudiosGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_course_audios(
    slug: str,
    payload: BatchAudioGenerationRequest,
    session: DBSession,
    current_user: AdminUser,
    audio_service: IAudioGenerationService,
) -> CourseAudiosGenerationResponse:
    """
    Generate audio for specific lessons in a course.

    - If lesson_ids is not provided: generates for all eligible lessons
    - If lesson_ids is []: generates nothing
    - If lesson_ids is [1, 2, 3]: generates only for those specific lessons

    Requires ``audio_config.voice_id`` applied to all lessons in the batch.

    Returns successful generations and any errors that occurred.
    """
    audio_config = AudioConfigDTO(
        voice_id=payload.audio_config.voice_id,
        speed=payload.audio_config.resolved_speed(),
    )

    request = CourseAudioGenerationRequestDTO(
        user_id=current_user.id,
        slug=slug,
        lesson_ids=payload.lesson_ids,
        audio_config=audio_config,
    )

    batch_result = await audio_service.generate_course_audios(
        session=session, request=request
    )

    return CourseAudiosGenerationResponse.from_batch_result(batch_result)


@router.get(
    "/{slug}/lessons/{id}/audio-status", response_model=AudioGenerationStatusResponse
)
async def get_lesson_audio_status(
    slug: str,
    session: DBSession,
    current_user: AuthenticatedUser,
    lesson_service: ILessonService,
    audio_service: IAudioGenerationService,
    lesson_id: int = Path(..., alias="id"),
) -> AudioGenerationStatusResponse:
    """
    Get the current audio generation status for a lesson.
    """
    lesson_dto = await lesson_service.get_course_lesson(
        session=session, slug=slug, lesson_id=lesson_id, current_user=current_user
    )

    playlist_url = lesson_dto.playlist_url
    active_job_id = None
    available_duration_ms = None
    estimated_total_duration_ms = None

    if lesson_dto.status == LessonStatus.AUDIO_GENERATING:
        active_job = await audio_service.get_active_job_for_lesson(
            session=session, lesson_id=lesson_id
        )
        if active_job is not None:
            active_job_id = active_job.job_id
            playlist_url = active_job.playlist_url
            available_duration_ms = active_job.available_duration_ms
            estimated_total_duration_ms = active_job.estimated_total_duration_ms

    return AudioGenerationStatusResponse(
        lesson_id=lesson_id,
        status=lesson_dto.status.value,
        playlist_url=playlist_url,
        active_job_id=active_job_id,
        available_duration_ms=available_duration_ms,
        estimated_total_duration_ms=estimated_total_duration_ms,
    )
