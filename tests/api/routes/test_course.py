import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from senda.api.schemas.responses.course import CourseResponse
from senda.domain.dtos.course import CourseDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.user import IUserRepository
from tests.utils import create_another_test_course, create_another_test_user


@pytest.mark.anyio
async def test_user_can_not_create_new_course(
    authorized_test_client: AsyncClient,
) -> None:
    payload = {
        "course": {
            "title": "Test Course1",
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": ["tag1", "tag2", "tag3"],
        }
    }
    response = await authorized_test_client.post(url="/courses", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_admin_can_create_new_course(admin_test_client: AsyncClient) -> None:
    payload = {
        "course": {
            "title": "Test Course1",
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": ["tag1", "tag2", "tag3"],
        }
    }
    response = await admin_test_client.post(url="/courses", json=payload)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.anyio
async def test_user_can_not_create_course_without_tags(
    authorized_test_client: AsyncClient,
) -> None:
    payload = {
        "course": {
            "title": "Test Course",
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": [],
        }
    }
    response = await authorized_test_client.post(url="/courses", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_admin_can_create_course_without_tags(
    admin_test_client: AsyncClient,
) -> None:
    payload = {
        "course": {
            "title": "Test Course",
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": [],
        }
    }
    response = await admin_test_client.post(url="/courses", json=payload)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.anyio
async def test_admin_can_create_course_without_duplicated_tags(
    admin_test_client: AsyncClient,
) -> None:
    payload = {
        "course": {
            "title": "Test Course",
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": ["tag1", "tag2", "tag2", "tag3", "tag3"],
        }
    }
    response = await admin_test_client.post(url="/courses", json=payload)
    course = CourseResponse(**response.json())
    assert set(course.course.tags) == {"tag1", "tag2", "tag3"}


@pytest.mark.anyio
async def test_admin_can_create_course_with_existing_title(
    admin_test_client: AsyncClient, test_course: CourseDTO
) -> None:
    payload = {
        "course": {
            "title": test_course.title,
            "difficultyLevel": "Beginner",
            "description": "test description",
            "tagList": test_course.tags,
        }
    }
    response = await admin_test_client.post(url="/courses", json=payload)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.anyio
async def test_user_can_retrieve_course_without_tags(
    authorized_test_client: AsyncClient,
    session: AsyncSession,
    user_repository: IUserRepository,
    course_repository: ICourseRepository,
) -> None:
    new_user = await create_another_test_user(
        session=session, user_repository=user_repository
    )
    new_course = await create_another_test_course(
        session=session, course_repository=course_repository, author_id=new_user.id
    )

    response = await authorized_test_client.get(url=f"/courses/{new_course.slug}")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_user_can_not_retrieve_not_existing_course(
    authorized_test_client: AsyncClient,
) -> None:
    response = await authorized_test_client.get(url="/courses/not-existing-course-slug")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_can_retrieve_course_if_exists(
    authorized_test_client: AsyncClient, test_course: CourseDTO
) -> None:
    response = await authorized_test_client.get(url=f"/courses/{test_course.slug}")
    course = CourseResponse(**response.json())
    assert course.course.slug == test_course.slug
    assert course.course.description == test_course.description
    assert course.course.difficulty_level == test_course.difficulty_level


@pytest.mark.anyio
async def test_admin_can_delete_a_existing_course_belonging_to_another_user(
    admin_test_client: AsyncClient,
    session: AsyncSession,
    user_repository: IUserRepository,
    course_repository: ICourseRepository,
) -> None:
    new_user = await create_another_test_user(
        session=session, user_repository=user_repository
    )
    new_course = await create_another_test_course(
        session=session, course_repository=course_repository, author_id=new_user.id
    )
    response = await admin_test_client.delete(url=f"/courses/{new_course.slug}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
