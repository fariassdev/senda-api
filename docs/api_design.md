# API Design: Course and Lesson Management

This document provides a high-level overview of the API for managing meditation courses and lessons within the Senda platform. It is designed to be a comprehensive guide for developers and users, detailing the API's capabilities, key resources, and future direction.

## Primary Goal

The primary goal of this API is to expose robust functionality to a front-end Content Management System (CMS) for:
-   **Automated Course and Lesson Generation:** Leveraging AI to create initial drafts of course structures and individual lesson scripts.
-   **Content Management:** Allowing for the review, editing, and activation of AI-generated content.
-   **Media Generation:** Facilitating the generation of audio files from lesson scripts.
-   **Status Tracking:** Providing mechanisms to track the generation and activation status of courses and lessons.

## Key Resources

-   **Course**: Represents a full meditation course. Courses are initially generated as drafts by the AI and contain a collection of lessons. They include an `active` status to indicate whether they have been reviewed and approved for use.
-   **Lesson**: Represents a single lesson within a course. Lessons can have their scripts generated on demand by the AI. The script content is stored directly within the lesson record as JSONB.

## Functionality

The API has been developed with the following key features in mind:

### AI-Powered Course Architecture

This functionality allows for the automated generation of course structures based on a user-provided prompt.

*   **Flow:**
    1.  A user provides a simple prompt (e.g., "Create a 15-day focused course on dealing with the loss of a loved one").
    2.  The AI "Course Architect" (currently implemented using Gemini) processes the prompt and generates a draft course structure, including course details and a breakdown of individual lessons.
    3.  The generated course is saved with an `active` status of `false`, requiring manual review and activation by a CMS user.
    4.  CMS users can then edit any parameter of the course or its lessons before activation.
*   **Implementation Details:**
    *   The "Course Architect" is designed as an interface, allowing for future integration with different AI providers (e.g., ChatGPT) without significant architectural changes.
    *   The AI output is a structured JSON, directly usable for database insertion.
    *   New API operations are available for editing course and lesson data.

### AI-Powered Lesson Script Generation

This feature enables the generation of detailed meditation scripts for individual lessons based on their existing data.

*   **Flow:**
    1.  A CMS user triggers script generation for a specific lesson or for all lessons within a course.
    2.  The AI "Lesson Script Writer" (currently implemented using Gemini) generates a detailed script based on the lesson's content.
    3.  The generated script is saved directly into the lesson's database record as JSONB (replacing the previous `script_url` field).
*   **Implementation Details:**
    *   The "Lesson Script Writer" is also designed as an interface for provider flexibility.
    *   Scripts are intended to be regenerated rather than manually edited, ensuring consistency with AI-generated content.

## Technical Specification

For a detailed technical definition of the API, including endpoints, request/response schemas, and data models, please refer to the OpenAPI specification. This document will be updated to reflect the new functionalities.

-   **[OpenAPI Specification](./openapi.yaml)**

## UI/UX Design

For a detailed description of the front-end application, its components, and user flows that will consume this API, please refer to the UI Design document.

-   **[UI Design Document](./ui_design.md)**

## Future Work

The following features are planned for future development:

1.  **Audio File Generation:** Implement functionality to generate audio files (e.g., MP3) from the saved lesson scripts.
2.  **Robust Test Suite:** Develop a comprehensive suite of automated tests to ensure the stability, reliability, and correctness of the API.
3.  **Generate course images**: Implement a image generation service to set representative course images following the Senda style, guidelines and philosophy.
4.  **Basic CMS UI:** Implement a foundational user interface for the CMS to facilitate interaction with the API's functionalities.
