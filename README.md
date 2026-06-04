<div align="center">

<img src="./public/logo.svg" width="150" height="150" alt="Senda Logo">

# Senda API

**AI-Powered REST API for Meditation Course Generation**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](./pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)](./pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](.)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](https://github.com/fariassdev/senda/blob/main/LICENSE)

Backend API built with **FastAPI** and **Python 3.12** for creating and managing meditation courses. Integrates **Google Gemini** for AI-powered script generation and dual TTS engines: **ChatterboxTTS** (GPU-accelerated on Modal.com) with **Kokoro TTS** (CPU-based fallback).

**Part of the [Senda Project](https://github.com/fariassdev/senda) — A multirepo coordinated with [Senda CMS](https://github.com/fariassdev/senda-cms)**

[Quick Start](#quick-start) • [Configuration](#configuration) • [API Documentation](#api-documentation) • [Development](#development)

</div>

## Overview

Senda API is the core backend service providing RESTful endpoints for meditation course management, AI-powered content generation, and audio production. Built with modern Python tooling and containerized for cloud deployment.

### Key Features

- **Course & Lesson Management** — CRUD operations for organizing meditation content
- **AI Script Generation** — Leverages Google Gemini to create unique, contextual meditation scripts
- **Dual TTS Engines** — GPU-accelerated ChatterboxTTS (primary, on Modal.com) with optional Kokoro TTS fallback
- **Voice Catalog** — Manage multiple voices with custom parameters and samples
- **Batch Operations** — Generate content for entire courses simultaneously
- **AWS S3 Storage** — Final audio files stored in S3 for reliable distribution
- **JWT Authentication** — Secure admin-only access control
- **RESTful API** — Comprehensive endpoints with Swagger/OpenAPI documentation
- **Cloud Ready** — Deployable to Google Cloud Run or any containerized environment

## Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager
- PostgreSQL 15+ (or use Docker)
- Access to external services (Google Gemini API key, etc.)

### Option 1: Docker (Recommended for Full Stack)

Start the entire Senda project from the root:

```bash
cd senda
make setup    # Builds and runs API + CMS + Database + TTS
```

### Option 2: Local Development (API Only)

**Setup:**

```bash
# Full setup (venv + dependencies + pre-commit hooks)
make setup

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database connection

# Run development server (with auto-reload)
make runserver-dev
```

The API will be available at `http://localhost:8081/api`

**Other useful commands:**

```bash
make test              # Run tests
make test-cov         # Run tests with coverage
make migrate          # Run database migrations
make check            # Lint + format + type checking
make help             # Show all available commands
```


## API Documentation

### Access Interactive Docs

Once the server is running, access API documentation at:

- **Swagger UI:** http://localhost:8081/api/docs
- **ReDoc:** http://localhost:8081/api/redoc
- **OpenAPI JSON:** http://localhost:8081/api/openapi.json

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/courses` | List all courses |
| `POST` | `/api/courses` | Create new course |
| `GET` | `/api/courses/{id}` | Get course details |
| `POST` | `/api/courses/{id}/generate-scripts` | Generate all scripts for course |
| `POST` | `/api/lessons/{id}/generate-audio` | Generate audio for lesson |
| `GET` | `/api/health` | Health check |

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/senda

# Authentication
JWT_SECRET=your-secret-key-here

# AI Services
GEMINI_API_KEY=your-gemini-api-key
KOKORO_API_URL=http://localhost:8880

# ChatterboxTTS on Modal (see docs/modal_setup.md for setup)
MODAL_TTS_ENDPOINT=https://username--senda-tts-chatterbox-synthesize.modal.run
MODAL_SYNC_VOICE_ENDPOINT=https://username--senda-tts-chatterbox-sync-voice.modal.run
MODAL_DELETE_VOICE_ENDPOINT=https://username--senda-tts-chatterbox-delete-voice.modal.run
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_ID=wk-xxxxxxxxxxxx
MODAL_PROXY_AUTH_TOKEN_SECRET=ws-xxxxxxxxxxxx

# AWS S3 (for audio storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=senda-ai
AWS_DEFAULT_REGION=eu-west-1
```

## Audio generation (Chatterbox + Kokoro)

Lesson audio uses a **catalog voice** (`voice_id`) and the voice's `tts_provider` (`chatterbox` on Modal GPU, or `kokoro` locally). Chatterbox requires Modal deployment and S3 for storage.

**Docs:** [Chatterbox TTS overview](./docs/chatterbox-tts.md) · [Modal setup](./docs/modal_setup.md)

Pipeline and failure semantics for voice creation/deletion live in `senda/services/voice_provisioning.py` (source of truth — keep docs in sync when changing behavior).

## Development

### Project Structure

```
senda/
├── app.py                      # FastAPI application entry point
├── api/                        # REST API layer
│   ├── router.py              # Main router configuration
│   ├── middlewares.py         # Auth, logging, error handling
│   ├── routes/                # Route handlers by domain
│   │   ├── authentication.py
│   │   ├── course.py
│   │   ├── lesson.py
│   │   ├── users.py
│   │   ├── profile.py
│   │   ├── tag.py
│   │   └── health_check.py
│   └── schemas/               # Request/Response schemas
│       ├── requests/          # Request DTOs
│       └── responses/         # Response DTOs
├── core/                       # Configuration & dependencies
│   ├── config.py              # Environment variables
│   ├── container.py           # Dependency injection container
│   ├── dependencies.py        # Dependency resolvers
│   ├── security.py            # JWT & authentication utilities
│   ├── exceptions.py          # Custom exceptions
│   ├── logging.py             # Logging configuration
│   ├── enums.py               # Shared enumerations
│   ├── settings/              # Settings configuration
│   └── utils/                 # Shared utilities
├── domain/                     # Domain models & repository interfaces
│   ├── dtos/                  # Data Transfer Objects
│   ├── exceptions/            # Domain-specific exceptions
│   ├── repositories/          # Abstract repository interfaces
│   ├── services/              # Service interfaces
│   ├── mapper.py              # Domain object mapping
│   └── utils/
├── infrastructure/             # Data access & external services
│   ├── alembic/               # Database migrations (Alembic)
│   ├── alembic.ini            # Alembic configuration
│   ├── models.py              # SQLAlchemy ORM models
│   ├── repositories/          # Repository implementations
│   ├── providers/             # External service clients
│   │   ├── gemini_*.py        # Google Gemini AI (scripts, courses)
│   │   ├── chatterbox_audio_provider.py   # Chatterbox synthesize (IAudioProvider)
│   │   ├── chatterbox_voice_asset_provisioner.py
│   │   ├── kokoro_audio_provider.py
│   │   ├── s3_storage_provider.py       # AWS S3 storage client
│   │   └── __init__.py
│   ├── modal/                 # Modal.com serverless deployments
│   │   └── tts/              # Text-to-Speech services
│   │       ├── main.py        # Modal app entry point
│   │       ├── chatterbox.py  # ChatterboxTTS endpoint
│   │       ├── voice_storage.py # Voice management (sync/delete)
│   │       ├── common.py       # Shared utilities
│   │       └── __init__.py
│   ├── utils/                 # Infrastructure utilities
│   │   ├── audio_processor.py # Audio composition & PCM handling
│   │   └── __init__.py
│   ├── loaders/               # Data loaders & fixtures
│   ├── mappers/               # DTO mappers
│   ├── prompts/               # AI prompt templates
│   └── config/                # Infrastructure configuration
└── services/                   # Business logic & use cases
    ├── auth.py
    ├── course.py
    ├── lesson.py
    ├── user.py
    ├── script_generation.py
    ├── audio_generation.py
    └── ...
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run tests in watch mode
make test-watch

# Or run directly with pytest (if needed)
pytest tests/
pytest tests/test_courses.py
pytest tests/test_courses.py::test_create_course
```

## Deployment

### Google Cloud Run

The API is deployed to Google Cloud Run for auto-scaling:

```bash
# Build container image
docker build -t senda-api:latest .

# Push to Google Container Registry
docker tag senda-api:latest gcr.io/YOUR-PROJECT/senda-api
docker push gcr.io/YOUR-PROJECT/senda-api

# Deploy to Cloud Run
gcloud run deploy senda-api \
  --image gcr.io/YOUR-PROJECT/senda-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=$DATABASE_URL,JWT_SECRET=$JWT_SECRET
```

### Requirements

- PostgreSQL 15+ (Neon for serverless)
- Kokoro TTS service (Oracle Cloud)
- Google Gemini API key
- AWS S3 credentials

## Contributing

Contributions welcome! Please open issues or pull requests.

## License

AGPL-3.0 License — see [LICENSE](https://github.com/fariassdev/senda/blob/main/LICENSE) for details
