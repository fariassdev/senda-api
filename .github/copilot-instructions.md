# Senda AI Platform - Copilot Instructions

## Project Overview
Senda is an AI-powered meditation course platform built with **Clean Architecture** principles. It generates meditation courses and lessons using Gemini AI, converts them to speech via Kokoro TTS, and stores audio on AWS S3. Recently migrated from monolithic architecture to clean architecture (PR #31).

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, Gemini AI, AWS S3, Kokoro TTS, UV package manager

## Architecture: Four-Layer Clean Architecture

The codebase strictly follows Clean Architecture with dependency inversion at every layer:

```
senda/
├── api/              # HTTP layer (routes, schemas, middleware)
├── services/         # Business logic implementations
├── domain/           # Business rules + interfaces (ABC only, no implementations)
│   ├── dtos/         # Data transfer objects
│   ├── repositories/ # Repository interfaces (ABC)
│   └── services/     # Service interfaces (ABC)
└── infrastructure/   # External services (DB, AI providers, storage)
    ├── models.py     # SQLAlchemy models
    ├── mappers/      # Model ↔ DTO conversion
    ├── repositories/ # Repository implementations
    └── providers/    # External API implementations (Gemini, S3, Kokoro)
```

**Critical Rule:** Domain layer (`domain/`) contains ONLY abstract interfaces (ABC). Never put implementations in domain layer - they belong in `services/` or `infrastructure/`.

## Dependency Injection Pattern

All dependencies flow through `senda/core/container.py` using constructor injection:

```python
# Container creates and wires dependencies
class Container:
    def course_service(self) -> ICourseService:
        return CourseService(
            course_repo=self.course_repository(),
            generation_provider=self.course_generation_provider()
        )
```

**FastAPI Integration:** Dependencies are injected via `senda/core/dependencies.py`:
```python
ICourseService = Annotated[CourseService, Depends(container.course_service)]
DBSession = Annotated[AsyncSession, Depends(container.session)]
```

**Usage in Routes:**
```python
async def create_course(
    session: DBSession,              # Auto-injected database session
    current_user: AuthenticatedUser,       # Auto-injected + authenticated user
    course_service: ICourseService,  # Auto-injected service
) -> CourseResponse:
    ...
```

## Data Flow & Mappers

**Model ↔ DTO Conversion:** Use dedicated mappers in `infrastructure/mappers/`:
- `UserModelMapper`, `CourseModelMapper`, `LessonModelMapper`, `TagModelMapper`
- Implement `IModelMapper[Model, DTO]` interface with `to_dto()` and `from_dto()`
- **Never** convert models directly - always use mappers

**Request/Response Conversion:**
- API schemas in `api/schemas/` have `.to_dto()` and `.from_dto()` methods
- Routes receive Request schemas → convert to DTOs → pass to services
- Services return DTOs → routes convert to Response schemas

## Development Workflow

**All commands use `uv run` - never use pip/python directly:**

```bash
make setup              # First-time setup (venv + deps + migrations)
make runserver-dev      # Dev server on :8081 with auto-reload
make test               # Run pytest with .env.test
make test-cov           # Tests with coverage report
make migration message="add field"  # Create Alembic migration
make migrate            # Apply migrations
make check              # Run all quality checks (lint + format + types)
make fix                # Auto-fix all issues
```

**Database:** PostgreSQL with async SQLAlchemy. Alembic config at `senda/infrastructure/alembic.ini`.

## Code Quality Standards

**Use Ruff for everything** (replaces black, isort, flake8, pyupgrade):
- `make lint` - Check linting
- `make format` - Check formatting
- `make types` - MyPy type checking
- `make fix` - Auto-fix lint + format issues

**Type Hints Required:** All functions/methods must have full type hints. Use `Any` for SQLAlchemy session types in repository interfaces.

**Import Order:** Ruff handles this automatically. First-party imports: `senda`.

## Key Patterns & Conventions

### 1. Repository Pattern
Repositories live in `infrastructure/repositories/` and implement interfaces from `domain/repositories/`:
```python
class CourseRepository(ICourseRepository):
    def __init__(self, course_mapper: IModelMapper):
        self._mapper = course_mapper

    async def add(self, session: Any, author_id: int, create_item: CreateCourseDTO) -> CourseRecordDTO:
        model = self._mapper.from_dto(create_item)
        session.add(model)
        await session.flush()
        return self._mapper.to_dto(model)
```

### 2. Service Pattern
Services in `services/` implement `domain/services/` interfaces and orchestrate business logic:
```python
class CourseService(ICourseService):
    def __init__(
        self,
        course_repo: ICourseRepository,
        generation_provider: ICourseGenerationProvider | None
    ):
        self._course_repo = course_repo
        self._generation_provider = generation_provider
```

### 3. Provider Pattern
External services (AI, storage, TTS) implement provider interfaces from `domain/services/`:
- `GeminiCourseGenerationProvider` → implements `ICourseGenerationProvider`
- `KokoroAudioProvider` → implements `IAudioProvider`
- `S3StorageProvider` → implements `IStorageProvider`

### 4. Authentication
- JWT tokens managed by `AuthTokenService`
- Token format: `Authorization: Token xxxxxx.yyyyyyy.zzzzzz` or `Authorization: Bearer xxxxxx.yyyyyyy.zzzzzz`
- Use `AdminUser` for Admin-protected routes, `AuthenticatedUser` dependency for protected routes, `OptionalUser` for public routes with optional auth

### 5. Error Handling
Custom exceptions in `domain/exceptions/` with matching HTTP handlers in `core/exceptions.py`:
```python
raise CourseNotFoundException(f"Course {slug} not found")  # → 404
raise InsufficientPermissionsException("Not authorized")   # → 403
raise AIProviderUnavailableException("Gemini unavailable") # → 503
```

## AI Integration Specifics

**Gemini AI:** Course/lesson generation via `infrastructure/providers/gemini_*_provider.py`
- Prompts loaded from `infrastructure/prompts/*.md`
- Uses structured output with Pydantic models
- Always check if provider exists (returns `None` if API key not configured)

**Audio Generation:** Multi-step async pipeline in `services/audio_generation.py`
- Parallel TTS processing (configurable concurrency via `MAX_CONCURRENT_TTS`)
- Lesson state machine: `DRAFT` → `SCRIPT_COMPLETED` → `AUDIO_COMPLETED`
- Chunked text processing for long scripts

**Prompts:** Stored as Markdown in `infrastructure/prompts/`, loaded via `PromptLoader`

## Testing Guidelines

- Tests in `tests/` mirror `senda/` structure
- Use fixtures from `tests/conftest.py` (test_user, test_course, authorized_test_client)
- Global Gemini API mock in conftest - configure per test:
  ```python
  def test_generation(mock_gemini_api_globally):
      mock_gemini_api_globally.return_value = CourseStructureDTO(...)
  ```
- All tests run with `.env.test` environment
- Database recreated for each test session

## Common Gotchas

1. **Don't bypass the container** - Always use DI, never instantiate services/repos directly
2. **Async all the way** - All DB operations are async (SQLAlchemy AsyncSession)
3. **Model conversion** - Use mappers for Model↔DTO, not manual assignment
4. **UV commands** - Use `uv run` prefix for all Python commands (not `python` or `pip`)
5. **Session management** - Never create sessions manually; use `DBSession` dependency
6. **Port 8081** - Dev server runs on 8081 (not 8000)

## File Organization Tips

- One entity = One file in each layer (user.py, course.py, lesson.py, etc.)
- DTOs grouped by entity in `domain/dtos/`
- API schemas split into `requests/` and `responses/`
- Keep provider implementations self-contained in `infrastructure/providers/`

## Additional Resources

- Dev commands: `SENDA_DEV_GUIDE.md`
- API docs: http://localhost:8081 (when server running)
