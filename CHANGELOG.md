# Changelog

All notable changes to the Senda API project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-04

### Added

- **Chatterbox TTS on Modal.com**: GPU-backed text-to-speech via a Modal deployment (`senda/infrastructure/modal/tts/`), with model weights cached in a dedicated Modal volume to reduce cold-start latency.
- **Voice catalog (admin)**: New `voices` table and `POST /voices`, `GET /voices`, `GET /voices/{slug}`, `PUT /voices/{voice_id}`, and `DELETE /voices/{voice_id}` endpoints for managing catalog voices with reference WAVs, preview samples, and S3 URLs.
- **Dual TTS provider registry**: `AudioGenerationService` selects `kokoro` or `chatterbox` from the catalog voice's `tts_provider` via a `TtsProvider`-keyed provider map.
- **`voice_id` on lessons**: Migration adds optional `lesson.voice_id` FK to record which catalog voice was used for generated audio.
- **Voice provisioning module**: `senda/services/voice_provisioning.py` documents and implements atomic create (`provision_voice_assets`) and delete (`deprovision_voice_assets`) pipelines across Modal, S3, and Postgres.
- **`IVoiceAssetProvisioner` port**: Provider-specific voice asset lifecycle (sync reference, preview TTS, remote delete) with `ChatterboxVoiceAssetProvisioner` implementation.
- **S3 generic upload/delete**: `IStorageProvider.upload_file` and `delete_file` for voice assets in addition to lesson audio uploads.
- **Dependency wiring module**: `senda/core/wiring/` extracts TTS, storage, and Gemini factory logic from `Container`.
- **Documentation**: `docs/chatterbox-tts.md` (overview) and `docs/modal_setup.md` (Modal deploy runbook).
- **Tests**: Unit suites for `VoiceService` and expanded `AudioGenerationService` coverage.

### Changed

- **Breaking — lesson audio requests**: `audio_config.voice_id` (UUID) is now **required** on single-lesson and batch course audio generation; the optional `voice` string override was removed.
- **Breaking — voice updates**: `PUT /voices/{voice_id}` no longer accepts `tts_provider` changes (metadata only: `is_active`, `description`).
- **Audio generation architecture**: TTS concurrency lives in `AudioGenerationService`; `AudioProcessor` only combines pre-generated PCM and exports MP3.
- **Batch course audio**: Each parallel lesson uses its own database session to avoid sharing an async SQLAlchemy session across concurrent tasks.
- **`IModelMapper`**: Instance methods instead of static methods (enables `VoiceModelMapper` with S3 base URL).
- **Voice API responses**: Include full public `reference_audio_url` and `sample_audio_url` values.
- **Terraform example**: Updated environment variable set for Modal and audio generation settings.

---

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

[0.2.0]: https://github.com/fariassdev/senda/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/fariassdev/senda/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fariassdev/senda/releases/tag/v0.1.0
