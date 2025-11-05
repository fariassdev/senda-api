import datetime
from dataclasses import dataclass, field

from senda.core.enums import UserRole


@dataclass
class UserDTO:
    id: int = field(init=False)
    username: str
    email: str
    password_hash: str
    bio: str | None
    image_url: str | None
    name: str | None
    role: UserRole
    created_at: datetime.datetime


@dataclass(frozen=True)
class CreatedUserDTO:
    id: int
    email: str
    username: str
    name: str | None
    bio: str | None
    image: str | None
    token: str


@dataclass(frozen=True)
class LoggedInUserDTO:
    email: str
    username: str
    name: str | None
    bio: str | None
    image: str | None
    token: str


@dataclass(frozen=True)
class UpdatedUserDTO:
    id: int
    email: str
    username: str
    name: str | None
    bio: str | None
    image: str | None


@dataclass(frozen=True)
class CreateUserDTO:
    username: str
    email: str
    password: str
    name: str | None = None
    role: UserRole = UserRole.USER


@dataclass(frozen=True)
class LoginUserDTO:
    email: str
    password: str


@dataclass(frozen=True)
class UpdateUserDTO:
    username: str | None = None
    email: str | None = None
    password: str | None = None
    name: str | None = None
    bio: str | None = None
    image_url: str | None = None
