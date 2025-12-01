from fastapi import APIRouter, BackgroundTasks, Path
from starlette import status

from senda.api.schemas.requests.lesson import (
    CreateLessonRequest,
    ReorderLessonsRequest,
    UpdateLessonRequest,
)
from senda.api.schemas.responses.audio_generation import (
    AudioGenerationResponse,
    AudioGenerationStatusResponse,
    CourseAudiosGenerationResponse,
)
from senda.api.schemas.responses.lesson import LessonResponse, LessonsListResponse
from senda.api.schemas.responses.script_generation import (
    CourseScriptsGenerationResponse,
    ScriptGenerationResponse,
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
from senda.core.exceptions import LessonNotFoundException
from senda.domain.dtos.audio_generation import (
    AudioGenerationRequestDTO,
    CourseAudioGenerationRequestDTO,
)
from senda.domain.dtos.script_generation import (
    CourseScriptRequestDTO,
    LessonScriptRequestDTO,
)

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
    response_model=ScriptGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_lesson_script(
    slug: str,
    session: DBSession,
    current_user: AdminUser,
    script_service: IScriptGenerationService,
    lesson_id: int = Path(..., alias="id"),
) -> ScriptGenerationResponse:
    """
    Generate script for a specific lesson.
    """
    request = LessonScriptRequestDTO(lesson_id=lesson_id, user_id=current_user.id)

    result = await script_service.generate_lesson_script(
        session=session, request=request
    )

    return ScriptGenerationResponse.from_dto(result)


@router.post(
    "/{slug}/generate-all-scripts",
    response_model=CourseScriptsGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_course_scripts(
    slug: str,
    session: DBSession,
    current_user: AdminUser,
    script_service: IScriptGenerationService,
) -> CourseScriptsGenerationResponse:
    """
    Generate scripts for all ungenerated lessons in a course.
    """
    request = CourseScriptRequestDTO(
        course_id=0,  # Will be resolved in service from slug
        user_id=current_user.id,
        slug=slug,
    )

    results = await script_service.generate_course_scripts(
        session=session, request=request
    )

    return CourseScriptsGenerationResponse.from_dtos(
        dtos=results, total_processed=len(results)
    )


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
    response_model=AudioGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_lesson_audio(
    slug: str,
    session: DBSession,
    current_user: AdminUser,
    audio_service: IAudioGenerationService,
    lesson_id: int = Path(..., alias="id"),
) -> AudioGenerationResponse:
    """
    Generate audio for a specific lesson.
    """
    request = AudioGenerationRequestDTO(lesson_id=lesson_id, user_id=current_user.id)

    result = await audio_service.generate_lesson_audio(session=session, request=request)

    return AudioGenerationResponse.from_dto(result)


@router.post(
    "/{slug}/generate-all-audios",
    response_model=CourseAudiosGenerationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_course_audios(
    slug: str,
    session: DBSession,
    current_user: AdminUser,
    audio_service: IAudioGenerationService,
) -> CourseAudiosGenerationResponse:
    """
    Generate audio for all script-completed lessons in a course.
    """
    request = CourseAudioGenerationRequestDTO(
        course_id=0, user_id=current_user.id, slug=slug
    )

    results = await audio_service.generate_course_audios(
        session=session, request=request
    )

    return CourseAudiosGenerationResponse.from_dtos(
        dtos=results, total_processed=len(results)
    )


@router.get(
    "/{slug}/lessons/{id}/audio-status", response_model=AudioGenerationStatusResponse
)
async def get_lesson_audio_status(
    slug: str,
    session: DBSession,
    current_user: AuthenticatedUser,
    lesson_service: ILessonService,
    lesson_id: int = Path(..., alias="id"),
) -> AudioGenerationStatusResponse:
    """
    Get the current audio generation status for a lesson.
    """
    lesson_record = await lesson_service._lesson_repo.get_or_none(
        session=session, lesson_id=lesson_id
    )

    if not lesson_record:
        raise LessonNotFoundException()

    return AudioGenerationStatusResponse(
        lesson_id=lesson_id,
        status=lesson_record.status.value,
        audio_url=lesson_record.audio_url,
    )
