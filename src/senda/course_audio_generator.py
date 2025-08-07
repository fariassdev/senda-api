#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re

# Import the refactored functions from your other scripts
from lesson_script_generator import generate_script
from lesson_audio_generator import generate_audio_from_script


def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def is_valid_json_file(filepath):
    """
    Checks if a file exists, is not empty, and contains valid JSON.
    """
    if not filepath.exists() or filepath.stat().st_size == 0:
        return False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def main():
    """
    Orchestrator script to generate all lesson scripts and audio files for a course.
    """
    # 1. Load the course structure JSON
    course_json_path = Path(__file__).parent / "introductory_course_structure.json"
    try:
        with open(course_json_path, "r", encoding="utf-8") as f:
            course_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Course structure file not found at '{course_json_path}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{course_json_path}'")
        return

    course_name = course_data.get("name", "Untitled Course")
    sanitized_course_name = sanitize_filename(course_name)

    # 2. Create a directory for the course output
    output_dir = (
        Path(__file__).parent.parent.parent
        / "generated_courses"
        / sanitized_course_name
    )
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory created at: '{output_dir}'")

    # Prepare the course context
    course_context = {
        "name": course_name,
        "description": course_data.get("description", ""),
        "totalLessons": course_data.get(
            "totalLessons", len(course_data.get("lessons", []))
        ),
    }

    # 3. Iterate over each lesson
    lessons = course_data.get("lessons", [])
    if not lessons:
        print("Warning: No lessons found in the course structure file.")
        return

    for lesson in lessons:
        lesson_number = lesson.get("lessonNumber", "N/A")
        lesson_title = lesson.get("title", "Untitled Lesson")
        print(f"\n--- Processing Lesson {lesson_number}: {lesson_title} ---")

        # Define file names
        sanitized_title = sanitize_filename(lesson_title)
        base_filename = f"{str(lesson_number).zfill(2)}_{sanitized_title}"
        script_filepath = output_dir / f"{base_filename}.json"
        audio_filepath = output_dir / f"{base_filename}.mp3"

        lesson_script_obj = None

        # --- Script Generation ---
        if is_valid_json_file(script_filepath):
            print(f"Valid script found at '{script_filepath}'. Loading from file.")
            with open(script_filepath, "r", encoding="utf-8") as f:
                lesson_script_obj = json.load(f)
        else:
            print(
                f"No valid script found for '{lesson_title}'. Generating new script..."
            )
            try:
                lesson_script_json_str = generate_script(course_context, lesson)
                lesson_script_obj = json.loads(
                    lesson_script_json_str
                )  # Parse to check validity before saving

                with open(script_filepath, "w", encoding="utf-8") as f:
                    json.dump(lesson_script_obj, f, indent=2)
                print(f"Script saved to '{script_filepath}'")

            except Exception as e:
                print(f"!! Failed to generate script for lesson {lesson_number}: {e}")
                if script_filepath.exists():
                    os.remove(script_filepath)  # Clean up potentially corrupt file
                continue

        # --- Audio Generation ---
        if audio_filepath.exists() and audio_filepath.stat().st_size > 0:
            print(
                f"Audio file already exists at '{audio_filepath}'. Skipping generation."
            )
        else:
            if lesson_script_obj:
                try:
                    print(f"Generating audio for '{lesson_title}'...")
                    generate_audio_from_script(lesson_script_obj, audio_filepath)
                except Exception as e:
                    print(
                        f"!! Failed to generate audio for lesson {lesson_number}: {e}"
                    )
            else:
                print(
                    "Skipping audio generation because the script is missing or invalid."
                )

    print("\n--- Course generation complete! ---")


if __name__ == "__main__":
    main()
