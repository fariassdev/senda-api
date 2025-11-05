from pydantic import BaseModel, EmailStr, Field

from senda.domain.dtos.user import CreateUserDTO, LoginUserDTO, UpdateUserDTO


class UserRegistrationData(BaseModel):
    email: EmailStr
    name: str | None = Field(None)
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3)


class UserLoginData(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdateData(BaseModel):
    email: str | None = Field(None)
    password: str | None = Field(None)
    username: str | None = Field(None)
    name: str | None = Field(None)
    bio: str | None = Field(None)
    image: str | None = Field(None)


class UserRegistrationRequest(BaseModel):
    user: UserRegistrationData

    def to_dto(self) -> CreateUserDTO:
        return CreateUserDTO(
            username=self.user.username,
            email=self.user.email,
            password=self.user.password,
            name=self.user.name,
        )


class UserLoginRequest(BaseModel):
    user: UserLoginData

    def to_dto(self) -> LoginUserDTO:
        return LoginUserDTO(email=self.user.email, password=self.user.password)


class UserUpdateRequest(BaseModel):
    user: UserUpdateData

    def to_dto(self) -> UpdateUserDTO:
        return UpdateUserDTO(
            email=self.user.email,
            password=self.user.password,
            username=self.user.username,
            name=self.user.name,
            bio=self.user.bio,
            image_url=self.user.image,
        )
