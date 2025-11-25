"""Tests for RBAC (Role-Based Access Control) functionality."""

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from senda.api.schemas.responses.gemini_schemas import GeminiCourseSchema
from senda.core.dependencies import IAuthTokenService
from senda.core.enums import DifficultyLevel, UserRole
from senda.domain.dtos.user import CreateUserDTO, UserDTO
from senda.domain.repositories.user import IUserRepository
from tests.conftest import mock_gemini_api_globally


class TestUserRegistration:
    """Test that registration creates USER role only."""

    @pytest.mark.anyio
    async def test_registration_creates_user_role(
        self,
        test_client: AsyncClient,
        session: AsyncSession,
        user_repository: IUserRepository,
    ):
        """Registration endpoint should create users with USER role only."""
        response = await test_client.post(
            "/users",
            json={
                "user": {
                    "username": "newuser",
                    "email": "newuser@test.com",
                    "password": "password123",
                    "name": "New User",
                }
            },
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify user role in DB
        user = await user_repository.get_by_email(session, "newuser@test.com")
        assert user.role == UserRole.USER


class TestAdminUserCreation:
    """Test admin user creation endpoint (admin-only)."""

    @pytest.mark.anyio
    async def test_admin_can_create_admin_user(self, admin_client: AsyncClient):
        """Admin users should be able to create other admin users."""
        response = await admin_client.post(
            "/user/admin",
            json={
                "user": {
                    "username": "newadmin",
                    "email": "newadmin@test.com",
                    "password": "adminpass123",
                    "name": "New Admin",
                }
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["username"] == "newadmin"
        assert data["user"]["role"] == "ADMIN"

    @pytest.mark.anyio
    async def test_regular_user_cannot_create_admin(
        self, authorized_test_client: AsyncClient
    ):
        """Regular users should get 403 when trying to create admin users."""
        response = await authorized_test_client.post(
            "/user/admin",
            json={
                "user": {
                    "username": "unauthorizedadmin",
                    "email": "unauth@test.com",
                    "password": "pass123",
                }
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["message"].lower()

    @pytest.mark.anyio
    async def test_unauthenticated_cannot_create_admin(self, test_client: AsyncClient):
        """Unauthenticated requests should get 403."""
        response = await test_client.post(
            "/user/admin",
            json={
                "user": {
                    "username": "unauthuser",
                    "email": "unauth@test.com",
                    "password": "pass123",
                }
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserPromotion:
    """Test user promotion to admin endpoint (admin-only)."""

    @pytest.mark.anyio
    async def test_admin_can_promote_user(
        self, admin_client: AsyncClient, test_user: UserDTO
    ):
        """Admin users should be able to promote regular users to admin."""
        response = await admin_client.put(f"/user/{test_user.id}/promote")

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["id"] == test_user.id
        assert data["user"]["role"] == "ADMIN"

    @pytest.mark.anyio
    async def test_regular_user_cannot_promote(
        self,
        authorized_test_client: AsyncClient,
        session: AsyncSession,
        user_repository: IUserRepository,
    ):
        """Regular users should get 403 when trying to promote users."""
        # Create another user to promote
        other_user_dto = CreateUserDTO(
            username="otheruser", email="other@test.com", password="pass123"
        )
        other_user = await user_repository.add(
            session=session, create_item=other_user_dto
        )

        response = await authorized_test_client.put(f"/user/{other_user.id}/promote")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_unauthenticated_cannot_promote(
        self, test_client: AsyncClient, test_user: UserDTO
    ):
        """Unauthenticated requests should get 403."""
        response = await test_client.put(f"/user/{test_user.id}/promote")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAIGenerationEndpoints:
    """Test that AI generation endpoints require admin role."""

    @pytest.mark.anyio
    async def test_admin_can_access_generate_course_endpoint(
        self, admin_client: AsyncClient
    ):
        """Admin users should be able to access the course generation endpoint."""
        response = await admin_client.post(
            "/courses/generate",
            json={
                "prompt": "Create a meditation course",
                "duration_days": 7,
                "difficulty_level": "Beginner",
            },
        )

        # Should not get 403 Forbidden (may get 500 or 503 due to AI service)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_regular_user_cannot_generate_course(
        self, authorized_test_client: AsyncClient
    ):
        """Regular users should get 403 when trying to generate courses."""
        response = await authorized_test_client.post(
            "/courses/generate",
            json={
                "prompt": "Create a meditation course",
                "duration_days": 7,
                "difficulty_level": "Beginner",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["message"].lower()

    @pytest.mark.anyio
    async def test_regular_user_cannot_generate_script(
        self, authorized_test_client: AsyncClient, test_course: UserDTO
    ):
        """Regular users should get 403 when trying to generate lesson scripts."""
        response = await authorized_test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-script"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_regular_user_cannot_generate_audio(
        self, authorized_test_client: AsyncClient, test_course: UserDTO
    ):
        """Regular users should get 403 when trying to generate audio."""
        response = await authorized_test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-audio"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeletionEndpoints:
    """Test that deletion endpoints require admin role."""

    @pytest.mark.anyio
    async def test_admin_can_delete_course(
        self, admin_client: AsyncClient, test_course: UserDTO
    ):
        """Admin users should be able to delete any course."""
        response = await admin_client.delete(f"/courses/{test_course.slug}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.anyio
    async def test_regular_user_cannot_delete_course(
        self, authorized_test_client: AsyncClient, test_course: UserDTO
    ):
        """Regular users should get 403 when trying to delete courses."""
        response = await authorized_test_client.delete(f"/courses/{test_course.slug}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_regular_user_cannot_delete_lesson(
        self, authorized_test_client: AsyncClient, test_course: UserDTO
    ):
        """Regular users should get 403 when trying to delete lessons."""
        response = await authorized_test_client.delete(
            f"/courses/{test_course.slug}/lessons/1"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestJWTRoleIntegrity:
    """Test that role changes in DB take effect immediately."""

    @pytest.mark.anyio
    async def test_role_from_db_is_used(
        self,
        application: FastAPI,
        session: AsyncSession,
        user_repository: IUserRepository,
        auth_token_service: IAuthTokenService,
    ):
        """Verify that role from DB is used, allowing real-time role changes."""
        # Create a user with USER role
        user_dto = CreateUserDTO(
            username="roletest",
            email="roletest@test.com",
            password="pass123",
            role=UserRole.USER,
        )
        user = await user_repository.add(session=session, create_item=user_dto)

        # Generate token
        token = auth_token_service.generate_jwt_token(user=user)

        # Verify user cannot access admin endpoint initially
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver/api",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            },
        ) as client:
            response = await client.post("/courses/generate", json={"prompt": "Test"})
            assert response.status_code == status.HTTP_403_FORBIDDEN

        # Now promote user in DB
        await user_repository.update_user_role(
            session=session, user_id=user.id, role=UserRole.ADMIN
        )
        await session.commit()

        # Same token should now have admin access (DB role changed)
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver/api",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            },
        ) as client:
            response = await client.post("/courses/generate", json={"prompt": "Test"})
            # Should NOT get 403 anymore (may get 500 due to mock issues)
            assert response.status_code != status.HTTP_403_FORBIDDEN
