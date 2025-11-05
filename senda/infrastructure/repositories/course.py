from datetime import datetime
from typing import Any

from sqlalchemy import case, delete, exists, func, insert, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import count

from senda.core.exceptions import CourseNotFoundException
from senda.core.utils.slug import (
    get_slug_unique_part,
    make_slug_from_title,
    make_slug_from_title_and_code,
)
from senda.domain.dtos.course import (
    CourseAuthorDTO,
    CourseDTO,
    CourseRecordDTO,
    CreateCourseDTO,
    UpdateCourseDTO,
)
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.course import ICourseRepository
from senda.infrastructure.models import Course, CourseTag, Favorite, Follower, Tag, User

# Aliases for the models if needed.
FavoriteAlias = aliased(Favorite)


class CourseRepository(ICourseRepository):
    def __init__(self, course_mapper: IModelMapper[Course, CourseRecordDTO]):
        self._course_mapper = course_mapper

    async def add(
        self, session: AsyncSession, author_id: int, create_item: CreateCourseDTO
    ) -> CourseRecordDTO:
        query = (
            insert(Course)
            .values(
                author_id=author_id,
                slug=make_slug_from_title(title=create_item.title),
                title=create_item.title,
                description=create_item.description,
                difficulty_level=create_item.difficulty_level,
                active=create_item.active,
                image_placeholder_url=create_item.image_placeholder_url,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            .returning(Course)
        )
        result = await session.execute(query)
        return self._course_mapper.to_dto(result.scalar())

    async def get_by_slug_or_none(
        self, session: AsyncSession, slug: str
    ) -> CourseRecordDTO | None:
        slug_unique_part = get_slug_unique_part(slug=slug)
        query = select(Course).where(
            Course.slug == slug or Course.slug.contains(slug_unique_part)
        )
        if course := await session.scalar(query):
            return self._course_mapper.to_dto(course)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> CourseRecordDTO:
        slug_unique_part = get_slug_unique_part(slug=slug)
        query = select(Course).where(
            Course.slug == slug or Course.slug.contains(slug_unique_part)
        )
        if not (course := await session.scalar(query)):
            raise CourseNotFoundException()
        return self._course_mapper.to_dto(course)

    async def get_by_id(
        self, session: AsyncSession, course_id: int
    ) -> CourseRecordDTO | None:
        query = select(Course).where(Course.id == course_id)
        if course := await session.scalar(query):
            return self._course_mapper.to_dto(course)
        return None

    async def delete_by_slug(self, session: AsyncSession, slug: str) -> None:
        query = delete(Course).where(Course.slug == slug)
        await session.execute(query)

    async def update_by_slug(
        self, session: AsyncSession, slug: str, update_item: UpdateCourseDTO
    ) -> CourseRecordDTO:
        query = (
            update(Course)
            .where(Course.slug == slug)
            .values(updated_at=datetime.now())
            .returning(Course)
        )
        if update_item.title is not None:
            updated_slug = make_slug_from_title_and_code(
                title=update_item.title, code=get_slug_unique_part(slug=slug)
            )
            query = query.values(title=update_item.title, slug=updated_slug)
        if update_item.description is not None:
            query = query.values(description=update_item.description)
        if update_item.difficulty_level is not None:
            query = query.values(difficulty_level=update_item.difficulty_level)
        if update_item.active is not None:
            query = query.values(active=update_item.active)
        if update_item.image_placeholder_url is not None:
            query = query.values(
                image_placeholder_url=update_item.image_placeholder_url
            )

        course = await session.scalar(query)
        return self._course_mapper.to_dto(course)

    async def list_by_followings(
        self, session: AsyncSession, user_id: int, limit: int, offset: int
    ) -> list[CourseRecordDTO]:
        query = (
            (
                select(
                    Course.id,
                    Course.author_id,
                    Course.slug,
                    Course.title,
                    Course.description,
                    Course.difficulty_level,
                    Course.active,
                    Course.image_placeholder_url,
                    Course.created_at,
                    Course.updated_at,
                    User.username,
                    User.bio,
                    User.image_url,
                )
            )
            .join(
                Follower,
                (
                    (Follower.following_id == Course.author_id)
                    & (Follower.follower_id == user_id)
                ),
            )
            .join(User, (User.id == Course.author_id))
            .order_by(Course.created_at)
        )
        query = query.limit(limit).offset(offset)
        courses = await session.execute(query)
        return [self._course_mapper.to_dto(course) for course in courses]

    async def list_by_followings_v2(
        self, session: AsyncSession, user_id: int, limit: int, offset: int
    ) -> list[CourseDTO]:
        query = (
            select(
                Course.id.label("id"),
                Course.author_id.label("author_id"),
                Course.slug.label("slug"),
                Course.title.label("title"),
                Course.description.label("description"),
                Course.difficulty_level.label("difficulty_level"),
                Course.active.label("active"),
                Course.image_placeholder_url.label("image_placeholder_url"),
                Course.created_at.label("created_at"),
                Course.updated_at.label("updated_at"),
                User.id.label("user_id"),
                User.username.label("username"),
                User.bio.label("bio"),
                User.email.label("email"),
                User.image_url.label("image_url"),
                true().label("following"),
                # Subquery for favorites count.
                select(func.count(Favorite.course_id))
                .where(Favorite.course_id == Course.id)
                .scalar_subquery()
                .label("favorites_count"),
                # Subquery to check if favorited by user with id `user_id`.
                exists()
                .where(
                    (Favorite.user_id == user_id) & (Favorite.course_id == Course.id)
                )
                .label("favorited"),
                # Concatenate tags.
                func.string_agg(Tag.tag, ", ").label("tags"),
            )
            .join(User, Course.author_id == User.id)
            .join(CourseTag, Course.id == CourseTag.course_id, isouter=True)
            .join(Tag, Tag.id == CourseTag.tag_id, isouter=True)
            .filter(
                User.id.in_(
                    select(Follower.following_id)
                    .where(Follower.follower_id == user_id)
                    .scalar_subquery()
                )
            )
            .group_by(
                Course.id,
                Course.author_id,
                Course.slug,
                Course.title,
                Course.description,
                Course.difficulty_level,
                Course.active,
                Course.image_placeholder_url,
                Course.created_at,
                Course.updated_at,
                User.id,
                User.username,
                User.bio,
                User.email,
                User.image_url,
            )
        )
        query = query.limit(limit).offset(offset)
        courses = await session.execute(query)

        return [self._to_course_dto(course) for course in courses]

    async def list_by_filters(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> list[CourseRecordDTO]:
        query = (
            select(
                Course.id,
                Course.author_id,
                Course.slug,
                Course.title,
                Course.description,
                Course.difficulty_level,
                Course.active,
                Course.image_placeholder_url,
                Course.created_at,
                Course.updated_at,
            )
        ).order_by(Course.created_at)

        if tag:
            # fmt: off
            query = query.join(
                CourseTag,
                (Course.id == CourseTag.course_id),
            ).where(
                CourseTag.tag_id == select(Tag.id).where(
                    Tag.tag == tag
                ).scalar_subquery()
            )
            # fmt: on

        if author:
            # fmt: off
            query = query.join(
                User,
                (User.id == Course.author_id)
            ).where(
                User.username == author
            )
            # fmt: on

        if favorited:
            # fmt: off
            query = query.join(
                Favorite,
                (Favorite.course_id == Course.id)
            ).where(
                Favorite.user_id == select(User.id).where(
                    User.username == favorited
                ).scalar_subquery()
            )
            # fmt: on

        query = query.limit(limit).offset(offset)
        courses = await session.execute(query)
        return [self._course_mapper.to_dto(course) for course in courses]

    async def list_by_filters_v2(
        self,
        session: AsyncSession,
        user_id: int | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> list[CourseDTO]:
        query = (
            # fmt: off
            select(
                Course.id.label("id"),
                Course.author_id.label("author_id"),
                Course.slug.label("slug"),
                Course.title.label("title"),
                Course.description.label("description"),
                Course.difficulty_level.label("difficulty_level"),
                Course.active.label("active"),
                Course.image_placeholder_url.label("image_placeholder_url"),
                Course.created_at.label("created_at"),
                Course.updated_at.label("updated_at"),
                User.id.label("user_id"),
                User.username.label("username"),
                User.bio.label("bio"),
                User.email.label("email"),
                User.image_url.label("image_url"),
                exists()
                .where(
                    (Follower.follower_id == user_id)
                    & (Follower.following_id == Course.author_id)
                )
                .label("following"),
                # Subquery for favorites count.
                select(func.count(Favorite.course_id))
                .where(Favorite.course_id == Course.id)
                .scalar_subquery()
                .label("favorites_count"),
                # Subquery to check if favorited by user with id `user_id`.
                exists()
                .where(
                    (Favorite.user_id == user_id) & (Favorite.course_id == Course.id)
                )
                .label("favorited"),
                # Concatenate tags.
                func.string_agg(Tag.tag, ", ").label("tags"),
            )
            .outerjoin(User, Course.author_id == User.id)
            .outerjoin(CourseTag, Course.id == CourseTag.course_id)
            .outerjoin(FavoriteAlias, FavoriteAlias.course_id == Course.id)
            .outerjoin(Tag, Tag.id == CourseTag.tag_id)
            .filter(
                # Filter by author username if provided.
                case((author is not None, User.username == author), else_=True),
                # Filter by tag if provided.
                case((tag is not None, Tag.tag == tag), else_=True),
                # Filter by "favorited by" username if provided.
                case(
                    (
                        favorited is not None,
                        FavoriteAlias.user_id
                        == select(User.id)
                        .where(User.username == favorited)
                        .scalar_subquery(),
                    ),
                    else_=True,
                ),
            )
            .group_by(
                Course.id,
                Course.author_id,
                Course.slug,
                Course.title,
                Course.description,
                Course.difficulty_level,
                Course.active,
                Course.image_placeholder_url,
                Course.created_at,
                Course.updated_at,
                User.id,
                User.username,
                User.bio,
                User.email,
                User.image_url,
            )
            # fmt: on
        )

        query = query.limit(limit).offset(offset)
        courses = await session.execute(query)
        return [self._to_course_dto(course) for course in courses]

    async def count_by_followings(self, session: AsyncSession, user_id: int) -> int:
        query = select(count(Course.id)).join(
            Follower,
            (
                (Follower.following_id == Course.author_id)
                & (Follower.follower_id == user_id)
            ),
        )
        result = await session.execute(query)
        return result.scalar()

    async def count_by_filters(
        self,
        session: AsyncSession,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> int:
        query = select(count(Course.id))

        if tag:
            # fmt: off
            query = query.join(
                CourseTag,
                (Course.id == CourseTag.course_id),
            ).where(
                CourseTag.tag_id == select(Tag.id).where(
                    Tag.tag == tag
                ).scalar_subquery()
            )
            # fmt: on

        if author:
            # fmt: off
            query = query.join(
                User,
                (User.id == Course.author_id)
            ).where(
                User.username == author
            )
            # fmt: on

        if favorited:
            # fmt: off
            query = query.join(
                Favorite,
                (Favorite.course_id == Course.id)
            ).where(
                Favorite.user_id == select(User.id).where(
                    User.username == favorited
                ).scalar_subquery()
            )
            # fmt: on

        result = await session.execute(query)
        return result.scalar()

    @staticmethod
    def _to_course_dto(res: Any) -> CourseDTO:
        return CourseDTO(
            id=res.id,
            author_id=res.author_id,
            slug=res.slug,
            title=res.title,
            description=res.description,
            difficulty_level=res.difficulty_level,
            active=res.active,
            image_placeholder_url=res.image_placeholder_url,
            tags=res.tags.split(", ") if res.tags else [],
            author=CourseAuthorDTO(
                username=res.username,
                bio=res.bio,
                image=res.image_url,
                following=res.following,
            ),
            created_at=res.created_at,
            updated_at=res.updated_at,
            favorited=res.favorited,
            favorites_count=res.favorites_count,
        )
