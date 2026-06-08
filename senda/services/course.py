import logging
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import DifficultyLevel, UserRole
from senda.core.exceptions import (
    CourseAlreadyFavoritedException,
    CourseGenerationException,
    CourseNotFavoritedException,
)
from senda.domain.dtos.course import (
    CourseAuthorDTO,
    CourseDTO,
    CourseRecordDTO,
    CoursesFeedDTO,
    CreateCourseDTO,
    UpdateCourseDTO,
)
from senda.domain.dtos.course_generation import (
    CourseGenerationRequestDTO,
    CourseStructureDTO,
)
from senda.domain.dtos.lesson import CreateLessonDTO, LessonDTO
from senda.domain.dtos.profile import ProfileDTO
from senda.domain.dtos.user import UserDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.course_tag import ICourseTagRepository
from senda.domain.repositories.favorite import IFavoriteRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.services.course import ICourseGenerationProvider, ICourseService
from senda.domain.services.profile import IProfileService

logger = logging.getLogger(__name__)


class CourseService(ICourseService):
    """Service to handle courses logic."""

    def __init__(
        self,
        course_repo: ICourseRepository,
        course_tag_repo: ICourseTagRepository,
        favorite_repo: IFavoriteRepository,
        profile_service: IProfileService,
        lesson_repo: ILessonRepository,
        generation_provider: ICourseGenerationProvider | None = None,
    ) -> None:
        self._course_repo = course_repo
        self._course_tag_repo = course_tag_repo
        self._favorite_repo = favorite_repo
        self._profile_service = profile_service
        self._lesson_repo = lesson_repo
        self._generation_provider = generation_provider

    async def create_new_course(
        self, session: AsyncSession, author_id: int, course_to_create: CreateCourseDTO
    ) -> CourseDTO:
        course = await self._course_repo.add(
            session=session, author_id=author_id, create_item=course_to_create
        )
        profile = await self._profile_service.get_profile_by_user_id(
            session=session, user_id=author_id
        )
        if course_to_create.tags:
            await self._course_tag_repo.add_many(
                session=session, course_id=course.id, tags=course_to_create.tags
            )
        return CourseDTO(
            **asdict(course),
            author=CourseAuthorDTO(
                username=profile.username,
                bio=profile.bio,
                image=profile.image,
                following=profile.following,
            ),
            tags=course_to_create.tags,
            favorited=False,
            favorites_count=0,
        )

    async def create_course_from_prompt(
        self, session: AsyncSession, request: CourseGenerationRequestDTO
    ) -> tuple[CourseDTO, list[LessonDTO]]:
        """
        Generates and creates a complete course with lessons using AI.

        Returns:
            Tuple of (CourseDTO, List[LessonDTO]) with complete data

        Raises:
            CourseGenerationException: If generation or creation fails
        """
        if not self._generation_provider:
            raise CourseGenerationException(
                message="AI generation provider not configured"
            )

        try:
            logger.info(
                f"Starting AI course generation for user {request.user_id}: "
                f"'{request.prompt[:100]}...'"
            )

            structure = await self._generation_provider.generate_course_structure(
                request
            )

            course_dto = structure_to_course_create_dto(structure, request.user_id)
            course = await self.create_new_course(
                session=session, author_id=request.user_id, course_to_create=course_dto
            )
            logger.info(f"Created course {course.id}: '{course.title}'")

            lessons = await self._create_lessons_for_course(
                session=session,
                course_id=course.id,
                author_id=request.user_id,
                structure=structure,
            )

            logger.info(
                f"Successfully created course {course.id} with {len(lessons)} lessons"
            )
            return course, lessons

        except CourseGenerationException:
            raise

        except Exception as e:
            logger.exception(f"Failed to create course from prompt: {e}")
            error_msg = f"Failed to create course: {type(e).__name__}"
            if str(e):
                error_msg += f" - {str(e)}"
            raise CourseGenerationException(message=error_msg) from e

    async def _create_lessons_for_course(
        self,
        session: AsyncSession,
        course_id: int,
        author_id: int,
        structure: CourseStructureDTO,
    ) -> list[LessonDTO]:
        """
        Creates all lessons for a generated course.

        Returns:
            List of created LessonDTOs
        """
        created_lessons: list[LessonDTO] = []

        for lesson_structure in structure.lessons:
            lesson_dto = CreateLessonDTO(
                lesson_number=lesson_structure.order,
                title=lesson_structure.title,
                core_practice=lesson_structure.core_practice,
                key_point=lesson_structure.key_point,
                tone=lesson_structure.tone,
                duration_minutes=lesson_structure.duration_minutes,
            )
            lesson_record = await self._lesson_repo.add(
                session=session,
                author_id=author_id,
                course_id=course_id,
                create_item=lesson_dto,
            )

            lesson = LessonDTO(
                id=lesson_record.id,
                course_id=lesson_record.course_id,
                lesson_number=lesson_record.lesson_number,
                title=lesson_record.title,
                core_practice=lesson_record.core_practice,
                key_point=lesson_record.key_point,
                tone=lesson_record.tone,
                duration_minutes=lesson_record.duration_minutes,
                status=lesson_record.status,
                script=None,
                script_generated_at=lesson_record.script_generated_at,
                created_at=lesson_record.created_at,
                updated_at=lesson_record.updated_at,
            )
            created_lessons.append(lesson)

        logger.info(f"Created {len(created_lessons)} lessons for course {course_id}")
        return created_lessons

    async def get_course_by_slug(
        self, session: AsyncSession, slug: str, current_user: UserDTO | None
    ) -> CourseDTO:
        course = await self._course_repo.get_by_slug(session=session, slug=slug)
        profile = await self._profile_service.get_profile_by_user_id(
            session=session, user_id=course.author_id, current_user=current_user
        )
        return await self._get_course_info(
            session=session,
            course=course,
            profile=profile,
            user_id=current_user.id if current_user else None,
        )

    async def delete_course_by_slug(
        self, session: AsyncSession, slug: str, current_user: UserDTO
    ) -> None:
        await self._course_repo.delete_by_slug(session=session, slug=slug)

    async def update_course_by_slug(
        self,
        session: AsyncSession,
        slug: str,
        course_to_update: UpdateCourseDTO,
        current_user: UserDTO,
    ) -> CourseDTO:
        course = await self._course_repo.get_by_slug(session=session, slug=slug)

        course = await self._course_repo.update_by_slug(
            session=session, slug=slug, update_item=course_to_update
        )
        profile = await self._profile_service.get_profile_by_user_id(
            session=session, user_id=course.author_id, current_user=current_user
        )
        return await self._get_course_info(
            session=session, course=course, profile=profile, user_id=current_user.id
        )

    async def get_courses_by_filters(
        self,
        session: AsyncSession,
        current_user: UserDTO | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> CoursesFeedDTO:
        courses = await self._course_repo.list_by_filters(
            session=session,
            limit=limit,
            offset=offset,
            tag=tag,
            author=author,
            favorited=favorited,
        )
        profiles_map = await self._get_profiles_mapping(
            session=session, courses=courses, current_user=current_user
        )
        courses_with_extra = [
            await self._get_course_info(
                session=session,
                course=course,
                profile=profiles_map[course.author_id],
                user_id=current_user.id if current_user else None,
            )
            for course in courses
        ]
        courses_count = await self._course_repo.count_by_filters(
            session=session, tag=tag, author=author, favorited=favorited
        )
        return CoursesFeedDTO(courses=courses_with_extra, courses_count=courses_count)

    async def get_courses_by_filters_v2(
        self,
        session: AsyncSession,
        current_user: UserDTO | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> CoursesFeedDTO:
        courses = await self._course_repo.list_by_filters_v2(
            session=session,
            user_id=current_user.id if current_user else None,
            limit=limit,
            offset=offset,
            tag=tag,
            author=author,
            favorited=favorited,
        )
        courses_count = await self._course_repo.count_by_filters(
            session=session, tag=tag, author=author, favorited=favorited
        )
        return CoursesFeedDTO(courses=courses, courses_count=courses_count)

    async def get_courses_feed(
        self, session: AsyncSession, current_user: UserDTO, limit: int, offset: int
    ) -> CoursesFeedDTO:
        courses = await self._course_repo.list_by_followings(
            session=session, user_id=current_user.id, limit=limit, offset=offset
        )
        profiles_map = await self._get_profiles_mapping(
            session=session, courses=courses, current_user=current_user
        )
        courses_with_extra = [
            await self._get_course_info(
                session=session,
                course=course,
                profile=profiles_map[course.author_id],
                user_id=current_user.id,
            )
            for course in courses
        ]
        courses_count = await self._course_repo.count_by_followings(
            session=session, user_id=current_user.id
        )
        return CoursesFeedDTO(courses=courses_with_extra, courses_count=courses_count)

    async def get_courses_feed_v2(
        self, session: AsyncSession, current_user: UserDTO, limit: int, offset: int
    ) -> CoursesFeedDTO:
        courses = await self._course_repo.list_by_followings_v2(
            session=session, user_id=current_user.id, limit=limit, offset=offset
        )
        courses_count = await self._course_repo.count_by_followings(
            session=session, user_id=current_user.id
        )
        return CoursesFeedDTO(courses=courses, courses_count=courses_count)

    async def add_course_into_favorites(
        self, session: AsyncSession, slug: str, current_user: UserDTO
    ) -> CourseDTO:
        course = await self.get_course_by_slug(
            session=session, slug=slug, current_user=current_user
        )
        if course.favorited:
            raise CourseAlreadyFavoritedException()

        await self._favorite_repo.create(
            session=session, course_id=course.id, user_id=current_user.id
        )
        return CourseDTO.with_updated_fields(
            dto=course,
            updated_fields={
                "favorited": True,
                "favorites_count": course.favorites_count + 1,
            },
        )

    async def remove_course_from_favorites(
        self, session: AsyncSession, slug: str, current_user: UserDTO
    ) -> CourseDTO:
        course = await self.get_course_by_slug(
            session=session, slug=slug, current_user=current_user
        )
        if not course.favorited:
            raise CourseNotFavoritedException()

        await self._favorite_repo.delete(
            session=session, course_id=course.id, user_id=current_user.id
        )
        return CourseDTO.with_updated_fields(
            dto=course,
            updated_fields={
                "favorited": False,
                "favorites_count": course.favorites_count - 1,
            },
        )

    async def _get_course_info(
        self,
        session: AsyncSession,
        course: CourseRecordDTO,
        profile: ProfileDTO,
        user_id: int | None = None,
    ) -> CourseDTO:
        article_tags = [
            tag.tag
            for tag in await self._course_tag_repo.list(
                session=session, course_id=course.id
            )
        ]
        favorites_count = await self._favorite_repo.count(
            session=session, course_id=course.id
        )
        is_favorited_by_user = (
            await self._favorite_repo.exists(
                session=session, author_id=user_id, course_id=course.id
            )
            if user_id
            else False
        )
        return CourseDTO(
            **asdict(course),
            author=CourseAuthorDTO(
                username=profile.username,
                bio=profile.bio,
                image=profile.image,
                following=profile.following,
            ),
            tags=article_tags,
            favorited=is_favorited_by_user,
            favorites_count=favorites_count,
        )

    async def _get_profiles_mapping(
        self,
        session: AsyncSession,
        courses: list[CourseRecordDTO],
        current_user: UserDTO | None,
    ) -> dict[int, ProfileDTO]:
        following_profiles = await self._profile_service.get_profiles_by_user_ids(
            session=session,
            user_ids=[course.author_id for course in courses],
            current_user=current_user,
        )
        return {profile.user_id: profile for profile in following_profiles}


def structure_to_course_create_dto(
    structure: CourseStructureDTO, author_id: int
) -> CreateCourseDTO:
    """
    Maps AI-generated structure to course creation DTO.

    Args:
        structure: CourseStructureDTO from AI generation
        author_id: ID of the course author

    Returns:
        CreateCourseDTO ready for repository persistence
    """
    return CreateCourseDTO(
        title=structure.title,
        description=structure.description,
        difficulty_level=structure.difficulty_level.value,
        tags=structure.tags,
        active=False,
    )
