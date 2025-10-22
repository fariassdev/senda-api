# Senda AI Assistant Instructions

This guide helps AI agents understand the key aspects of the Senda codebase for effective development assistance.

## Architecture Overview

Senda is a meditation content generation platform with three core services:
- **FastAPI Backend** (`src/`): Manages courses and lessons with AI-powered content generation
- **PostgreSQL Database**: Stores course/lesson data with UUIDv7 primary keys (port 5433)
- **Kokoro TTS**: Local text-to-speech service for audio generation (port 8880)

Key components:
```
src/
├── main.py          # Entry point (runs server)
├── api.py           # FastAPI app & routes
├── services/         # Core business logic
│   ├── course_architect/     # AI course generation (Gemini)
│   ├── lesson_script_writer/ # AI script generation (Gemini)
│   ├── audio_service.py     # TTS + S3 integration
│   ├── lesson_script_service.py  # Orchestrates script generation
│   ├── auth_service.py      # JWT authentication logic
│   ├── event_publisher.py   # Redis pub/sub for WebSocket events
│   └── s3_service.py        # AWS S3 file uploads
├── models/           # SQLAlchemy models (Course, Lesson, User)
├── repositories/     # Database operations layer
├── routers/          # FastAPI endpoints (/courses, /lessons, /auth, /ws)
├── schemas/          # Pydantic request/response models
├── core/             # Database connection + auth + Redis utilities
└── utils/            # UUIDv7 generation utilities
```

## Development Workflow

### 1. Setup (mandatory venv activation)

Before running any Python command in this repository you MUST activate the project's virtual environment. Failing to activate the venv can cause dependency, linting, formatting, or runtime errors. CI pipelines must also use the pinned environment or lockfile.

Windows (PowerShell - recommended):
```powershell
# activate the venv in PowerShell (mandatory before running python/uv commands)
. .venv\Scripts\Activate.ps1

# install editable package
uv pip install -e .
```

Windows (cmd.exe):
```bat
# activate the venv in cmd.exe (mandatory before running python/uv commands)
.venv\Scripts\activate

# install editable package
uv pip install -e .
```

Unix / macOS (bash/zsh):
```bash
# activate the venv (mandatory before running python/uv commands)
source .venv/bin/activate

# install editable package
uv pip install -e .
```

CI note: ensure CI creates and activates the same venv or uses the repository lockfile to reproduce the exact environment before running linters and tests.

### 2. Configuration
- Copy `.env.example` to `.env`
- **Required**: `GEMINI_API_KEY` for AI generation
- **Database**: PostgreSQL on port 5433 (non-standard to avoid conflicts)
- **Authentication**: Generate JWT secret with `openssl rand -hex 32`
- **AWS**: Configure S3 credentials for audio storage

### 3. Running Services
```powershell
# Start PostgreSQL + Kokoro TTS (Docker)
docker-compose up --build

# Run API locally (recommended for development)
uvicorn api:app --reload

# With debug logging
uvicorn api:app --reload --log-level debug

# Or using Python directly
python -m main
```

**API Endpoints:**
- Swagger docs: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- Health check: `http://localhost:8000/api/health`

### 4. Database Migrations
```powershell
# Generate an empty migration template. Then you MUST modify the generated file to add the desired changes.
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Critical Patterns

### 1. Repository Pattern (Strictly Enforced)
**Never use SQLAlchemy models directly in routers.** All database operations go through repository classes:

```python
# ❌ WRONG - Direct model usage in router
from models.lesson import Lesson
lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()

# ✅ CORRECT - Use repository
from repositories.lesson import LessonRepository
lesson_repo = LessonRepository(db)
lesson = lesson_repo.get_lesson(lesson_id)
```

Example: `src/senda/api/repositories/lesson.py` for reference implementation.

### 2. Dependency Injection Pattern
All services use FastAPI's `Depends()` for injection:

```python
def get_lesson_repository(db: Session = Depends(get_db)) -> LessonRepository:
    return LessonRepository(db)

@router.get("/lessons/{lesson_id}")
def get_lesson(
    lesson_id: UUID,
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
):
    return lesson_repo.get_lesson(lesson_id)
```

Example: `src/senda/api/routers/course.py` for dependency chain patterns.

### 3. AI Generation Pipeline
**Two-stage generation process:**

1. **Course Architecture** (via `GeminiCourseArchitect`):
   - Input: User prompt
   - Output: `CourseCreate` schema with lessons list
   - System prompt: `services/course_architect/system_prompt.md`
   - Uses Gemini's structured JSON response mode

2. **Lesson Scripts** (via `GeminiLessonScriptWriter`):
   - Input: Course context + lesson details
   - Output: `List[ScriptPart]` with speak/pause actions
   - System prompt: `services/lesson_script_writer/system_prompt.md`
   - Stored as JSONB in PostgreSQL (not external files)

Example: See `services/course_architect/gemini_course_architect.py` for Gemini API configuration with `response_schema` and `thinking_config`.

### 4. Lesson Status State Machine
```
PENDING → SCRIPT_GENERATING → SCRIPT_COMPLETED → AUDIO_GENERATING → AUDIO_COMPLETED
         ↓                     ↓
         SCRIPT_FAILED         AUDIO_FAILED
```

**Critical:** Always check `lesson.status` before operations. Status tracked in `models/lesson.py:LessonStatus` enum.

### 5. Asynchronous Processing Pattern
Background tasks via FastAPI's `BackgroundTasks` for long-running operations:

```python
# In-memory tracking sets prevent duplicate operations
_generating_courses = set()  # in routers/course.py
_generating_lessons = set()  # in routers/lesson.py

# Check before starting background task
if course_id in _generating_courses:
    raise HTTPException(status_code=409, detail="Course generation already in progress")

_generating_courses.add(course_id)
background_tasks.add_task(_generate_course_task, course_id, ...)
```

**⚠️ Limitation**: No persistent task queue - background tasks reset on server restart. Consider adding Celery/Redis for production.

### 6. Script Data Structure
Scripts are `List[ScriptPart]` with two action types:

```python
# Speak action - generates audio via TTS
{"type": "speak", "content": "Close your eyes and take a deep breath..."}

# Pause action - inserts silence
{"type": "pause", "duration": 3.0}  # seconds
```

Audio generation in `services/audio_service.py` processes these sequentially, concatenates audio, and uploads to S3.

### 7. UUIDv7 for Primary Keys
All entities use UUIDv7 (time-ordered UUIDs) for better database performance:

```python
from utils.uuid_utils import generate_uuidv7

class Lesson(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuidv7)
```

**Why UUIDv7?** Time-ordered structure reduces B-tree index fragmentation compared to random UUIDv4. Implementation in `utils/uuid_utils.py`.

### 8. Authentication & Rate Limiting
- **JWT-based authentication** with access tokens (30 min) and refresh tokens (7 days)
- **Rate limiting** via `slowapi`:
  - Login: 5 attempts/minute per IP
  - Token refresh: 10 attempts/minute per IP
- **Security**: Passwords hashed with bcrypt, refresh tokens hashed before storage
- Example: `routers/auth.py` for `@limiter.limit()` decorator usage

### 9. Pydantic Schema Aliases
Schemas use camelCase for API (JavaScript convention) but snake_case internally:

```python
class LessonBase(BaseModel):
    lesson_number: int = Field(..., alias="lessonNumber")
    core_practice: str = Field(..., alias="corePractice")
    
    class Config:
        populate_by_name = True  # Accept both camelCase and snake_case
```

### 10. Import Conventions
**Keep `__init__.py` files empty.** All imports should be direct to specific files to make dependencies explicit and avoid circular imports:

```python
# ✅ CORRECT - Direct imports
from services.lesson_script_service import LessonScriptService
from repositories.lesson import LessonRepository
from models.lesson import Lesson

# ❌ AVOID - Package-level imports that could create circular dependencies
from services import LessonScriptService  # If __init__.py had imports
from models import Lesson  # If __init__.py had imports
```

This pattern ensures:
- **Explicit dependencies**: Clear which specific modules are imported
- **No circular imports**: Empty `__init__.py` files prevent import cycles
- **Better IDE support**: Direct imports are easier to trace and refactor

- **Package Management**: `uv` (not pip/poetry) - faster, resolves dependencies better
- **AI**: `google-genai==1.28.0` (Gemini) for content generation
- **Database**: `sqlalchemy==2.0.42` + `psycopg[binary,pool]==3.2.9` + `alembic==1.16.4`
- **API**: `fastapi==0.116.1` + `uvicorn[standard]==0.0.35.0`
- **Audio**: `pydub==0.25.1` + `pyaudio==0.2.14` for audio processing
- **Storage**: `boto3==1.40.7` for S3 audio uploads
- **Auth**: `PyJWT==2.10.1` + `bcrypt==5.0.0` + `slowapi==0.1.9` (rate limiting)

## Integration Points

### 1. Gemini AI
- **Usage**: Course structure + script generation with structured JSON responses
- **Configuration**: System instructions from markdown files, structured output via `response_schema`
- **Example**: `GeminiCourseArchitect` uses `response_schema=CourseCreate` for type-safe generation

### 2. Kokoro TTS
- **Endpoint**: `http://localhost:8880/v1/audio/speech`
- **Voice**: `af_nicole` (default)
- **Format**: PCM stream, converted to MP3 via pydub
- **Integration**: `services/audio_service.py` handles streaming + concatenation

### 3. AWS S3
- **Purpose**: Store generated audio files
- **Naming**: `audio/{lesson_id}_{title}_{random}.mp3`
- **Service**: `services/s3_service.py` with boto3 client

### 4. PostgreSQL
- **Port**: 5433 (non-standard to avoid conflicts)
- **JSONB**: Scripts stored as JSONB for flexible querying
- **Pooling**: Connection pool managed by SQLAlchemy (`DB_POOL_MIN=2`, `DB_POOL_MAX=10`)

## Development Notes

- **Python Version**: Requires 3.13+
- **Docker Compose**: Includes DB + TTS, but API typically runs locally during development
- **Environment**: Use `.env` file for secrets, never commit it
- **Scripts**: AI-generated scripts are regenerated, not edited - AI is source of truth
- **Error Handling**: Background task errors log to console (needs improvement for production)
- **CORS**: Configured for `http://localhost:3000` (frontend development)
- **Pre-commit**: Configured with ruff for linting (see `.pre-commit-config.yaml`)

## Common Tasks

### Generate a course
```powershell
# POST /api/courses with prompt
# Returns Course with PENDING lessons
# Use BackgroundTasks to generate all lesson scripts
```

### Generate lesson script
```powershell
# POST /api/lessons/{lesson_id}/generate
# Updates status to SCRIPT_GENERATING → SCRIPT_COMPLETED/SCRIPT_FAILED
# Returns immediately, generation runs in background
```

### Generate audio
```powershell
# POST /api/lessons/{lesson_id}/generate-audio
# Requires lesson.status == SCRIPT_COMPLETED
# Updates status to AUDIO_GENERATING → AUDIO_COMPLETED/AUDIO_FAILED
```

### Check migration status
```powershell
alembic current
alembic history
```