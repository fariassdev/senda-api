import os
import json
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

from src.senda.api.schemas.lesson import ScriptPart
from .lesson_script_writer import LessonScriptWriter

load_dotenv()


class GeminiLessonScriptWriter(LessonScriptWriter):
    """
    An implementation of the LessonScriptWriter that uses the Google Gemini API
    to generate meditation scripts for lessons.
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.system_instruction = self._load_system_instruction()
        self.response_schema = list[ScriptPart]

    def generate_script(
        self, course_context: dict[str, any], lesson_details: dict[str, any]
    ) -> list[ScriptPart]:
        """
        Generates a meditation script using the Gemini API and parses it into a list of script parts.
        """
        prompt_input = json.dumps(
            {"courseContext": course_context, "lessonDetails": lesson_details}, indent=2
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt_input),
                ],
            ),
        ]

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
            ),
            response_mime_type="application/json",
            response_schema=self.response_schema,
            system_instruction=self.system_instruction,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return response.parsed

    def _load_system_instruction(self) -> list[types.Part]:
        prompt_path = Path(__file__).parent / "system_prompt.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
        return [types.Part.from_text(text=prompt_text)]


# For testing purposes
if __name__ == "__main__":
    writer = GeminiLessonScriptWriter()
    mock_course_context = {
        "name": "The First Path",
        "description": "A 10-day introductory course to build a foundational meditation practice...",
        "totalLessons": 10,
    }
    mock_lesson_details = {
        "lessonNumber": 1,
        "title": "The First Step",
        "corePractice": "Resting your attention on the physical sensation of your breath...",
        "durationMinutes": 6,
        "keyPoint": "The goal isn't to stop thinking...",
        "tone": "Gentle, welcoming, reassuring",
    }
    try:
        generated_script = writer.generate_script(
            mock_course_context, mock_lesson_details
        )
        print("Successfully generated script:")
        for part in generated_script:
            print(part.model_dump_json(indent=2))
    except Exception as e:
        print(f"An error occurred: {e}")
