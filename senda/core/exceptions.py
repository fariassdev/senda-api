from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from senda.core.utils.errors import format_errors


class BaseInternalException(Exception):
    """
    Base error class for inherit all internal errors.
    """

    _status_code = 0
    _message = ""
    _errors: dict = {}

    def __init__(
        self,
        status_code: int | None = None,
        message: str | None = None,
        errors: dict[str, dict[Any, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.errors = errors

    def __str__(self) -> str:
        return self.get_message()

    def get_status_code(self) -> int:
        return self.status_code or self._status_code

    def get_message(self) -> str:
        return self.message or self._message

    def get_errors(self) -> dict[str, dict[Any, Any]]:
        return self.errors or self._errors

    @classmethod
    def get_response(cls) -> JSONResponse:
        return JSONResponse(
            status_code=cls._status_code,
            content={
                "status": "error",
                "status_code": cls._status_code,
                "type": cls.__name__,
                "message": cls._message,
                "errors": cls._errors,
            },
        )


class UserNotFoundException(BaseInternalException):
    """Exception raised when user not found in database."""

    _status_code = 404
    _message = "User with this username does not exist."


class CourseNotFoundException(BaseInternalException):
    """Exception raised when course not found in database."""

    _status_code = 404
    _message = "Course with this slug does not exist."


class CourseAlreadyFavoritedException(BaseInternalException):
    """Exception raised when course already marked favorited."""

    _status_code = 400
    _message = "Course has already been marked as a favorite."


class CourseNotFavoritedException(BaseInternalException):
    """Exception raised when course is not favorited."""

    _status_code = 400
    _message = "Course is not favorited."


class LessonNotFoundException(BaseInternalException):
    """Exception raised when lesson not found in database."""

    _status_code = 404
    _message = "Lesson with this id does not exist."


class VoiceNotFoundException(BaseInternalException):
    """Exception raised when voice not found in database."""

    _status_code = 404
    _message = "Voice with this identifier does not exist."


class AudioGenerationJobNotFoundException(BaseInternalException):
    """Exception raised when an audio generation job is not found."""

    _status_code = 404
    _message = "Audio generation job with this id does not exist."


class VoiceSlugAlreadyExistsException(BaseInternalException):
    """Exception raised when a voice slug is already in the catalog."""

    _status_code = 409
    _message = "A voice with this slug already exists."


class VoiceInUseException(BaseInternalException):
    """Exception raised when a voice is referenced by one or more lessons."""

    _status_code = 409
    _message = "This voice is in use by one or more lessons and cannot be deleted."


class UnsupportedVoiceTtsProviderException(BaseInternalException):
    """Exception raised when POST /voices requests an unsupported tts_provider."""

    _status_code = 400
    _message = "Only the chatterbox provider is supported when creating catalog voices."


class AudioVoiceRequiredException(BaseInternalException):
    """Exception raised when audio generation is requested without a catalog voice."""

    _status_code = 400
    _message = "audio_config.voice_id is required to generate lesson audio."


class VoiceNotActiveException(BaseInternalException):
    """Exception raised when the selected catalog voice is inactive."""

    _status_code = 400
    _message = "The selected voice is not active."


class EmailAlreadyTakenException(BaseInternalException):
    """Exception raised when email was found in database while registration."""

    _status_code = 400
    _message = "User with this email already exists."
    _errors = {"email": ["user with this email already exists."]}


class UserNameAlreadyTakenException(BaseInternalException):
    """Exception raised when username was found in database while registration."""

    _status_code = 400
    _message = "User with this username already exists."
    _errors = {"username": ["user with this username already exists."]}


class IncorrectLoginInputException(BaseInternalException):
    """Exception raised when email or password was incorrect while login."""

    _status_code = 400
    _message = "Incorrect email or password."
    _errors = {
        "email": ["incorrect email or password."],
        "password": ["incorrect email or password."],
    }


class IncorrectJWTTokenException(BaseInternalException):
    """Exception raised when user provided invalid JWT token."""

    _status_code = 403
    _message = "Invalid JWT token."


class ProfileNotFoundException(BaseInternalException):
    """Exception raised when specific profile not found."""

    _status_code = 404
    _message = "Profile with this username does not exist."


class OwnProfileFollowingException(BaseInternalException):
    """Exception raised when user is trying to follow own profile."""

    _status_code = 403
    _message = "Own profile cannot be followed or unfollowed."


class ProfileAlreadyFollowedException(BaseInternalException):
    """Exception raised when user is trying to follow already followed profile."""

    _status_code = 400
    _message = "Profile already followed."


class ProfileNotFollowedFollowedException(BaseInternalException):
    """Exception raised when user is trying to unfollow not followed profile."""

    _status_code = 400
    _message = "Profile was not followed."


class RateLimitExceededException(BaseInternalException):
    """Exception raised when rate limit exceeded during specific time."""

    _status_code = 429
    _message = "Rate limit exceeded. Please try again later."


class CourseGenerationException(BaseInternalException):
    """Exception raised when AI course generation fails."""

    _status_code = 500
    _message = "Course generation failed."


class InvalidPromptException(BaseInternalException):
    """Exception raised when the AI prompt is invalid or violates content policy."""

    _status_code = 400
    _message = "Invalid prompt provided for course generation."


class AIProviderUnavailableException(BaseInternalException):
    """Exception raised when the AI provider service is unavailable."""

    _status_code = 503
    _message = "AI service temporarily unavailable. Please try again later."


class ScriptGenerationException(BaseInternalException):
    """Exception raised when lesson script generation fails."""

    _status_code = 500
    _message = "Script generation failed."


class AudioGenerationException(BaseInternalException):
    """Exception raised when audio generation fails."""

    _status_code = 500
    _message = "Audio generation failed."


class InvalidLessonStateException(BaseInternalException):
    """Exception raised when lesson is not in valid state for audio generation."""

    _status_code = 400
    _message = "Lesson must have SCRIPT_COMPLETED, AUDIO_COMPLETED, or AUDIO_FAILED status to generate audio."


class AudioProviderException(BaseInternalException):
    """Exception raised when TTS provider fails to generate audio."""

    _status_code = 502
    _message = "Failed to generate audio from text-to-speech service."


class StorageProviderException(BaseInternalException):
    """Exception raised when storage provider fails to upload audio."""

    _status_code = 502
    _message = "Failed to upload audio to storage service."


class InsufficientPermissionsException(BaseInternalException):
    """Exception raised when user lacks required permissions for action."""

    _status_code = 403
    _message = "You don't have permission to perform this action."


def add_internal_exception_handler(app: FastAPI) -> None:
    """
    Handle all internal exceptions.
    """

    @app.exception_handler(BaseInternalException)
    async def _exception_handler(
        _: Request, exc: BaseInternalException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.get_status_code(),
            content={
                "status": "error",
                "status_code": exc.get_status_code(),
                "type": type(exc).__name__,
                "message": exc.get_message(),
                "errors": exc.get_errors(),
            },
        )


def add_request_exception_handler(app: FastAPI) -> None:
    """
    Handle request validation errors exceptions.
    """

    @app.exception_handler(RequestValidationError)
    async def _exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "status_code": 422,
                "type": "RequestValidationError",
                "message": "Schema validation error",
                "errors": format_errors(errors=exc.errors()),
            },
        )


def add_http_exception_handler(app: FastAPI) -> None:
    """
    Handle http exceptions.
    """

    @app.exception_handler(HTTPException)
    async def _exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "status_code": exc.status_code,
                "type": "HTTPException",
                "message": exc.detail,
            },
        )


def add_exception_handlers(app: FastAPI) -> None:
    """
    Set all exception handlers to app object.
    """
    add_internal_exception_handler(app=app)
    add_request_exception_handler(app=app)
    add_http_exception_handler(app=app)
