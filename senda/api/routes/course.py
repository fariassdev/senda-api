from fastapi import APIRouter, HTTPException
from starlette import status

from senda.api.schemas.requests.course import CreateCourseRequest, UpdateCourseRequest
from senda.api.schemas.requests.course_generation import CourseGenerationRequest
from senda.api.schemas.responses.course import CourseResponse, CoursesFeedResponse
from senda.api.schemas.responses.course_generation import CourseGenerationResponse
from senda.core.dependencies import (
    CurrentAdminUser,
    CurrentOptionalUser,
    CurrentUser,
    DBSession,
    ICourseService,
    Pagination,
    QueryFilters,
)
from senda.core.exceptions import (
    AIProviderUnavailableException,
    CourseGenerationException,
    InvalidPromptException,
)

router = APIRouter()


@router.get("/feed", response_model=CoursesFeedResponse)
async def get_course_feed(
    pagination: Pagination,
    session: DBSession,
    current_user: CurrentUser,
    course_service: ICourseService,
) -> CoursesFeedResponse:
    """
    Get course feed from following users.
    """
    courses_feed_dto = await course_service.get_courses_feed_v2(
        session=session,
        current_user=current_user,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return CoursesFeedResponse.from_dto(dto=courses_feed_dto)


@router.get("", response_model=CoursesFeedResponse)
async def get_global_course_feed(
    pagination: Pagination,
    courses_filters: QueryFilters,
    session: DBSession,
    current_user: CurrentOptionalUser,
    course_service: ICourseService,
) -> CoursesFeedResponse:
    """
    Get global course feed.
    """
    courses_feed_dto = await course_service.get_courses_by_filters_v2(
        session=session,
        current_user=current_user,
        tag=courses_filters.tag,
        author=courses_filters.author,
        favorited=courses_filters.favorited,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return CoursesFeedResponse.from_dto(dto=courses_feed_dto)


@router.get("/{slug}", response_model=CourseResponse)
async def get_course(
    slug: str,
    session: DBSession,
    current_user: CurrentOptionalUser,
    course_service: ICourseService,
) -> CourseResponse:
    """
    Get course by slug.
    """
    course_dto = await course_service.get_course_by_slug(
        session=session, slug=slug, current_user=current_user
    )
    return CourseResponse.from_dto(dto=course_dto)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CreateCourseRequest,
    session: DBSession,
    current_user: CurrentUser,
    course_service: ICourseService,
) -> CourseResponse:
    """
    Create new course.
    """
    course_dto = await course_service.create_new_course(
        session=session, author_id=current_user.id, course_to_create=payload.to_dto()
    )
    return CourseResponse.from_dto(dto=course_dto)


@router.post(
    "/generate",
    response_model=CourseGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate course from AI prompt",
    responses={
        201: {"description": "Course successfully generated and created"},
        400: {"description": "Invalid prompt or parameters"},
        503: {"description": "AI service unavailable"},
    },
)
async def generate_course(
    payload: CourseGenerationRequest,
    session: DBSession,
    current_user: CurrentAdminUser,
    course_service: ICourseService,
) -> CourseGenerationResponse:
    """
    Generates a complete course structure using AI and creates it in the database.

    The AI will create:
    - Course title and description
    - Appropriate difficulty level
    - Daily lessons with titles, practices, key points
    - Estimated duration for each lesson
    - Relevant tags

    The generated course is saved as a draft with all lessons created.
    Lesson scripts can be generated separately using the lesson endpoints.

    Returns the complete course data including all generated lessons.
    """
    try:
        generation_request = payload.to_dto(user_id=current_user.id)

        course, lessons = await course_service.create_course_from_prompt(
            session=session, request=generation_request
        )

        return CourseGenerationResponse.from_dto(course_dto=course, lessons=lessons)

    except InvalidPromptException as e:
        raise e

    except AIProviderUnavailableException as e:
        raise e

    except CourseGenerationException as e:
        raise e


@router.put("/{slug}", response_model=CourseResponse)
async def update_course(
    slug: str,
    payload: UpdateCourseRequest,
    session: DBSession,
    current_user: CurrentUser,
    course_service: ICourseService,
) -> CourseResponse:
    """
    Update a course.
    """
    course_dto = await course_service.update_course_by_slug(
        session=session,
        slug=slug,
        course_to_update=payload.to_dto(),
        current_user=current_user,
    )
    return CourseResponse.from_dto(dto=course_dto)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    slug: str,
    session: DBSession,
    current_user: CurrentAdminUser,
    course_service: ICourseService,
) -> None:
    """
    Delete a course by slug.
    """
    await course_service.delete_course_by_slug(
        session=session, slug=slug, current_user=current_user
    )


@router.post("/{slug}/favorite", response_model=CourseResponse)
async def favorite_course(
    slug: str,
    session: DBSession,
    current_user: CurrentUser,
    course_service: ICourseService,
) -> CourseResponse:
    """
    Favorite a course.
    """
    course_dto = await course_service.add_course_into_favorites(
        session=session, slug=slug, current_user=current_user
    )
    return CourseResponse.from_dto(dto=course_dto)


@router.delete("/{slug}/favorite", response_model=CourseResponse)
async def unfavorite_course(
    slug: str,
    session: DBSession,
    current_user: CurrentUser,
    course_service: ICourseService,
) -> CourseResponse:
    """
    Unfavorite a course.
    """
    course_dto = await course_service.remove_course_from_favorites(
        session=session, slug=slug, current_user=current_user
    )
    return CourseResponse.from_dto(dto=course_dto)
