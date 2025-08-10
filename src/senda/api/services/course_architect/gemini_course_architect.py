import os
import json
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv
from .course_architect import CourseArchitect
from src.senda.api.schemas.course import CourseCreate

load_dotenv()


class GeminiCourseArchitect(CourseArchitect):
    """
    An implementation of the CourseArchitect that uses the Google Gemini API
    to generate the course structure.
    """

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.system_instruction = self._load_system_instruction()
        self.response_schema = self._build_response_schema()

    def generate_course_structure(self, prompt: str) -> CourseCreate:
        """Generates a course structure using the Gemini API and parses it into a CourseCreate object."""
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1,
            ),
            safety_settings=self._get_safety_settings(),
            response_mime_type="application/json",
            response_schema=self.response_schema,
            system_instruction=self.system_instruction,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generate_content_config,
        )

        response_json = json.loads(response.text)
        return CourseCreate.model_validate(response_json)

    def _load_system_instruction(self) -> list[types.Part]:
        prompt_path = Path(__file__).parent / "system_prompt.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
        return [types.Part.from_text(text=prompt_text)]

    def _get_safety_settings(self) -> list[types.SafetySetting]:
        return [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"
            ),
        ]

    def _build_response_schema(self) -> genai.types.Schema:
        # In a real app, this could also be loaded from a JSON file
        return genai.types.Schema(
            type=genai.types.Type.OBJECT,
            description="A complete meditation course structure, including metadata and a full list of lesson plans.",
            required=["name", "description", "totalLessons", "tags", "lessons"],
            properties={
                "name": genai.types.Schema(type=genai.types.Type.STRING),
                "description": genai.types.Schema(type=genai.types.Type.STRING),
                "totalLessons": genai.types.Schema(type=genai.types.Type.INTEGER),
                "tags": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(type=genai.types.Type.STRING),
                ),
                "lessons": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        required=[
                            "lessonNumber",
                            "title",
                            "corePractice",
                            "durationMinutes",
                            "keyPoint",
                            "tone",
                        ],
                        properties={
                            "lessonNumber": genai.types.Schema(
                                type=genai.types.Type.INTEGER
                            ),
                            "title": genai.types.Schema(type=genai.types.Type.STRING),
                            "corePractice": genai.types.Schema(
                                type=genai.types.Type.STRING
                            ),
                            "durationMinutes": genai.types.Schema(
                                type=genai.types.Type.INTEGER
                            ),
                            "keyPoint": genai.types.Schema(
                                type=genai.types.Type.STRING
                            ),
                            "tone": genai.types.Schema(type=genai.types.Type.STRING),
                        },
                    ),
                ),
            },
        )


# For testing purposes
if __name__ == "__main__":
    architect = GeminiCourseArchitect()
    test_prompt = "Create a 7-day course on mindfulness for anxiety."
    try:
        generated_course = architect.generate_course_structure(test_prompt)
        print("Successfully generated course:")
        print(generated_course.model_dump_json(indent=2))
    except Exception as e:
        print(f"An error occurred: {e}")
