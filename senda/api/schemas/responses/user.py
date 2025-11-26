from pydantic import BaseModel

from senda.core.enums import UserRole
from senda.domain.dtos.user import (
    CreatedUserDTO,
    LoggedInUserDTO,
    UpdatedUserDTO,
    UserDTO,
)


class UserIDData(BaseModel):
    id: int


class UserBaseData(BaseModel):
    email: str
    username: str
    name: str | None
    bio: str | None
    image: str | None
    token: str


class LoggedInUserData(UserBaseData):
    pass


class RegisteredUserData(UserIDData, UserBaseData):
    pass


class AuthenticatedUserData(UserIDData, UserBaseData):
    pass


class UpdatedUserData(UserIDData, UserBaseData):
    pass


class UserRegistrationResponse(BaseModel):
    user: RegisteredUserData

    @classmethod
    def from_dto(cls, dto: CreatedUserDTO) -> "UserRegistrationResponse":
        return UserRegistrationResponse(
            user=RegisteredUserData(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                name=dto.name,
                bio=dto.bio,
                image=dto.image,
                token=dto.token,
            )
        )


class UserLoginResponse(BaseModel):
    user: LoggedInUserData

    @classmethod
    def from_dto(cls, dto: LoggedInUserDTO) -> "UserLoginResponse":
        return UserLoginResponse(
            user=LoggedInUserData(
                email=dto.email,
                username=dto.username,
                name=dto.name,
                bio=dto.bio,
                image=dto.image,
                token=dto.token,
            )
        )


class AuthenticatedUserResponse(BaseModel):
    user: AuthenticatedUserData

    @classmethod
    def from_dto(cls, dto: UserDTO, token: str) -> "AuthenticatedUserResponse":
        return AuthenticatedUserResponse(
            user=AuthenticatedUserData(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                name=dto.name,
                bio=dto.bio,
                image=dto.image_url,
                token=token,
            )
        )


class UpdatedUserResponse(BaseModel):
    user: UpdatedUserData

    @classmethod
    def from_dto(cls, dto: UpdatedUserDTO, token: str) -> "UpdatedUserResponse":
        return UpdatedUserResponse(
            user=UpdatedUserData(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                name=dto.name,
                bio=dto.bio,
                image=dto.image,
                token=token,
            )
        )


class AdminUserData(BaseModel):
    """Admin user data with role information."""

    id: int
    email: str
    username: str
    name: str | None
    role: str


class AdminUserCreationResponse(BaseModel):
    """Response for admin user creation."""

    user: AdminUserData

    @classmethod
    def from_dto(cls, dto: UserDTO) -> "AdminUserCreationResponse":
        return AdminUserCreationResponse(
            user=AdminUserData(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                name=dto.name,
                role=dto.role.value,
            )
        )


class UserPromotionResponse(BaseModel):
    """Response for user promotion to admin."""

    user: AdminUserData

    @classmethod
    def from_dto(cls, dto: UserDTO) -> "UserPromotionResponse":
        return UserPromotionResponse(
            user=AdminUserData(
                id=dto.id,
                email=dto.email,
                username=dto.username,
                name=dto.name,
                role=dto.role.value,
            )
        )
