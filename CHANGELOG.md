# Changelog

All notable changes to the Senda API project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-12-23

### Added

- **Docker build optimization**: Added `.dockerignore` file to exclude unnecessary files from Docker builds, reducing image size and build time. Excluded patterns include:
  - Development tools (`.vscode`, `.idea`, `.editorconfig`)
  - Cache directories (`.mypy_cache`, `.ruff_cache`, `.pytest_cache`)
  - CI/CD and documentation (`.github`, `.bmad`, `.agent`, `.claude`)
  - Build artifacts and configurations (`Makefile`, `helm-charts`, `coverage*`)

- **Configurable TTS timeout**: Added new environment variable `KOKORO_API_TIMEOUT` to configure the timeout for TTS (Text-to-Speech) API requests. Default value is 60 seconds, which is helpful for:
  - Remote server connections with higher latency
  - Cold starts on serverless infrastructure
  - CPU-based Kokoro TTS processing (which takes considerably longer than GPU)

### Fixed

- **Audio export functionality**: Added `ffmpeg` to the Docker image to enable audio export features. Previously, audio export would fail in containerized environments due to the missing `ffmpeg` dependency.

### Changed

- **Terraform configuration**: Updated `terraform.tfvars.example` with complete list of environment variables including AWS S3 configuration options.

### Documentation

- Enhanced `.env.example` with improved comments explaining the purpose and recommended values for configuration options, particularly around CORS and TTS timeout settings.

---

## [0.1.0] - 2025-12-19

### Added

- Initial release of Senda API
- Core domain models for courses, lessons, and audio content
- RESTful API endpoints for course management
- AI-powered content generation using Google Gemini
- Text-to-Speech audio generation using Kokoro TTS
- AWS S3 integration for audio storage
- JWT-based authentication
- PostgreSQL database integration
- Docker containerization support
- Terraform infrastructure as code

---

[0.1.1]: https://github.com/fariassdev/senda/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fariassdev/senda/releases/tag/v0.1.0
