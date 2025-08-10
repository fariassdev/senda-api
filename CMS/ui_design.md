# UI/UX Design Specification: Senda CMS

This document outlines the design and user experience for the Senda Content Management System (CMS) front-end.

## 1. Overview

The CMS provides an interface to manage guided meditation courses. It allows a user to view the structure of a course, see the status of each lesson, and trigger the generation of lesson scripts and audio files.

## 2. Screens and Layouts

### 2.1. Course Details Screen

This is the main screen of the application.

**Layout:**
- **Header:**
  - `[Image Placeholder]`: A placeholder for the course cover image (e.g., 600x400px).
  - `[Course Title]`: The main title of the course.
  - `[Course Description]`: A brief description of the course.
  - `[Author]`: The author of the course.
- **Global Actions:**
  - `[Button: "Generate All Lessons"]`: A primary button that triggers the generation for all lessons that are not yet `COMPLETED`.
- **Lesson List:**
  - A vertically stacked list of all lessons in the course, rendered as `LessonListItem` components.

## 3. Components

### 3.1. LessonListItem

This component represents a single lesson in the `LessonList`. It is expandable and displays different controls based on its state.

**Collapsed View (Default):**
- `[Lesson Number]`: e.g., "Lesson 1"
- `[Lesson Title]`: e.g., "The First Step"
- `[Duration]`: e.g., "10 min"
- `[Status Icon]`: An icon representing the current `LessonStatus`.
- `[Action Button]`: A button to trigger an action (e.g., "Generate").

**Expanded View (On Click):**
- Shows all information from the collapsed view.
- `[Core Practice]`: The core practice of the lesson.
- `[Key Point]`: The key learning point.
- `[Tone]`: The desired tone for the narration.
- **Generated Files:**
  - `[Button: "View Script"]`: Visible if `scriptUrl` exists. Opens the JSON script in a new tab or modal.
  - `[Audio Player]`: An HTML5 audio player. Visible if `audioUrl` exists.

---

## 4. Component States and User Flows

This section details the different visual states of the `LessonListItem` based on the `LessonStatus` enum from the API.

### 4.1. State: `NOT_GENERATED`

- **Description:** The initial state for a lesson before any generation has been attempted.
- **Status Icon:** ⚪ (Empty Circle)
- **Action Button:** `[Button: "Generate"]`
- **User Flow:**
  1. User clicks "Generate".
  2. A `POST` request is sent to `/api/courses/{courseId}/lessons/{lessonId}/generate`.
  3. The UI immediately updates the lesson's state to `GENERATING`.

### 4.2. State: `GENERATING`

- **Description:** The lesson script and/or audio are currently being generated on the backend.
- **Status Icon:** ⏳ (Hourglass) or a spinning loader.
- **Action Button:** `[Button: "Generating..."]` (Disabled, with a spinner icon).
- **User Flow:**
  1. The UI enters this state after triggering generation.
  2. The frontend should periodically poll the `GET /api/courses/{courseId}` endpoint (e.g., every 5 seconds) to check for status changes.
  3. When the status changes to `COMPLETED` or `FAILED`, the UI updates to the corresponding state.

### 4.3. State: `COMPLETED`

- **Description:** The lesson script and audio have been successfully generated.
- **Status Icon:** ✅ (Green Checkmark)
- **Action Button:** `[Button: "Regenerate"]`
- **User Flow:**
  1. In the expanded view, "View Script" and the audio player are now visible and functional.
  2. User can click "Regenerate" to trigger the generation process again (same flow as `NOT_GENERATED`).

### 4.4. State: `FAILED`

- **Description:** An error occurred during the generation process.
- **Status Icon:** ❌ (Red X)
- **Action Button:** `[Button: "Retry Generation"]`
- **User Flow:**
  1. The user can click "Retry Generation" to attempt the process again (same flow as `NOT_GENERATED`).
  2. The UI could show an error message on hover over the status icon or in the expanded view if the API provides one.

### 4.5. Global Action: "Generate All Lessons"

- **User Flow:**
  1. User clicks the "Generate All Lessons" button.
  2. A `POST` request is sent to `/api/courses/{courseId}/generate-all`.
  3. The UI finds all lessons with the status `NOT_GENERATED` or `FAILED` and updates their state to `GENERATING`.
  4. The polling mechanism begins, refreshing the status of all lessons until none are left in the `GENERATING` state.
