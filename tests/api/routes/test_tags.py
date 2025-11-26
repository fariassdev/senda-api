import pytest
from httpx import AsyncClient

from senda.domain.dtos.course import CourseDTO


@pytest.mark.anyio
async def test_empty_list_when_no_tags_exist(test_client: AsyncClient) -> None:
    response = await test_client.get(url="/tags")
    assert response.json() == {"tags": []}


@pytest.mark.anyio
async def test_list_of_tags_when_course_with_tags_exists(
    authorized_test_client: AsyncClient, test_course: CourseDTO
) -> None:
    response = await authorized_test_client.get(url="/tags")
    response_tags = response.json()["tags"]
    assert len(response_tags) == len(set(test_course.tags))
    assert all(tag in test_course.tags for tag in response_tags)
