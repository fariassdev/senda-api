# API Design: Course and Lesson Management

This document provides a high-level overview of the API for managing meditation courses and lessons.

The primary goal of this API is to expose functionality to a front-end CMS for:
- Viewing course structures.
- Triggering the generation of lesson scripts (JSON).
- Triggering the generation of lesson audio (MP3).
- Tracking the status of each lesson.

## Key Resources

- **Course**: Represents a full meditation course, containing a collection of lessons.
- **Lesson**: Represents a single lesson within a course, which can be generated on demand.

## Technical Specification

For a detailed technical definition of the API, including endpoints, request/response schemas, and data models, please refer to the OpenAPI specification.

- **[OpenAPI Specification](./openapi.yaml)**

## UI/UX Design

For a detailed description of the front-end application, its components, and user flows that will consume this API, please refer to the UI Design document.

- **[UI Design Document](./ui_design.md)**
