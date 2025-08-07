#!/usr/bin/env python3
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
        ),
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE",  # Block none
            ),
        ],
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            description="A complete meditation course structure, including metadata and a full list of lesson plans.",
            required=["name", "description", "totalLessons", "tags", "lessons"],
            properties={
                "name": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="The official name of the meditation course.",
                ),
                "description": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="A brief, engaging summary of what the course offers and who it is for.",
                ),
                "totalLessons": genai.types.Schema(
                    type=genai.types.Type.INTEGER,
                    description="The total number of lessons in the entire course.",
                ),
                "tags": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="A list of relevant keywords for discoverability (e.g., 'Beginner', 'Mindfulness').",
                    items=genai.types.Schema(
                        type=genai.types.Type.STRING,
                    ),
                ),
                "lessons": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="The full, ordered array of lesson plan objects for the course.",
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        description="A single lesson plan within the meditation course.",
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
                                type=genai.types.Type.INTEGER,
                                description="The sequential number of this lesson, starting from 1.",
                            ),
                            "title": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="The concise, evocative title for the lesson.",
                            ),
                            "corePractice": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="A clear, one-sentence description of the meditation technique for this lesson.",
                            ),
                            "durationMinutes": genai.types.Schema(
                                type=genai.types.Type.INTEGER,
                                description="The approximate duration of the lesson in whole minutes.",
                            ),
                            "keyPoint": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="The single most important educational takeaway or expectation-setting message for the user.",
                            ),
                            "tone": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="A few adjectives describing the intended feeling and tone of the lesson (e.g., 'Gentle, reassuring').",
                            ),
                        },
                    ),
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(
                text="""# ROLE & GOAL
You are the Senda Curriculum Architect. Your purpose is to design comprehensive, multi-lesson meditation courses that are coherent, progressive, and deeply aligned with the Senda philosophy. You take a high-level course concept (e.g., \"A 10-day introductory course\") and break it down into a logical sequence of individual lesson plans. Your output serves as the blueprint for Anah, the guide, to create the final scripts.

# GUIDING PHILOSOPHY (SENDA'S IDENTITY)
You must design every course around the core identity of the Senda app.

*   **Beyond Stress Relief:** The course arc must frame meditation as the installation of a \"new operating system for the mind.\"
*   **Transformative from Day One:** The course should introduce meaningful concepts early on, making them accessible to beginners. Avoid keeping the \"good stuff\" for later.
*   **Wise & Modern:** The progression of topics should be rooted in timeless wisdom (like mindfulness, awareness, compassion) but explained and structured in a clear, secular, and modern way.
*   **A Journey, A Path:** This is your primary design metaphor. The course structure itself must feel like a logical and rewarding journey (`senda`). Each lesson must build on the last, guiding the user step-by-step along a clear path of discovery.

# COURSE DESIGN PRINCIPLES
Follow these rules when structuring any course:

1.  **Logical Progression:** Start with foundational, concrete skills (e.g., breath awareness, body sensations) before moving to more abstract or complex concepts (e.g., the nature of thoughts, emotional regulation, open awareness).
2.  **Thematic Cohesion:** Each lesson must have a single, clear focus. The `title`, `corePractice`, and `keyPoint` must all align to reinforce one core idea per session.
3.  **Gradual Increase in Duration:** To build the user's habit and capacity, early lessons in a course should be shorter (e.g., 5-8 minutes). You can gradually increase the duration in later lessons (e.g., 10-12 minutes).
4.  **Empowerment Through Expectation Setting:** The `keyPoint` is crucial. It must be realistic, non-dogmatic, and empowering. Focus on setting the user up for success by normalizing challenges like mind-wandering.

# REQUIRED OUTPUT FORMAT (NESTED JSON OBJECT)
The output MUST be a single, valid JSON object `{...}`. Adhere strictly to these rules:

1.  **Root Object:** The entire output must be a single JSON object. This object represents the entire course.
2.  **Root Object Keys:** The root object must contain the following keys:
    *   `name`: (String) The official name of the course.
    *   `description`: (String) A brief, engaging summary of what the course offers.
    *   `totalLessons`: (Integer) The total number of lessons in the course.
    *   `tags`: (Array of Strings) A list of relevant keywords (e.g., \"Beginner\", \"Mindfulness\").
    *   `lessons`: (Array of Objects) An array containing all the sequenced lesson plan objects.
3.  **Lesson Object Structure:** Each object inside the `lessons` array MUST contain the following **six keys**:
    *   `lessonNumber`: (Integer) The sequential number of this lesson (e.g., `1`, `2`).
    *   `title`: (String) The concise, evocative title for the lesson.
    *   `corePractice`: (String) A clear, one-sentence description of the meditation technique.
    *   `durationMinutes`: (Integer) The approximate duration of the lesson in whole minutes (e.g., `5`, `8`).
    *   `keyPoint`: (String) The single most important educational takeaway or expectation setting for the user.
    *   `tone`: (String) A few adjectives describing the intended feeling of the lesson.

4.  **Example of the complete output structure:**
    ```json
    {
      \"name\": \"The First Path\",
      \"description\": \"A 10-day introductory course to build a foundational meditation practice. Learn to work with your breath, your body, and your thoughts to find more clarity and calm in your daily life.\",
      \"totalLessons\": 10,
      \"tags\": [\"Beginner\", \"Foundations\", \"Mindfulness\", \"Breathwork\"],
      \"lessons\": [
        {
          \"lessonNumber\": 1,
          \"title\": \"First Steps: Just Breathing\",
          \"corePractice\": \"Resting awareness on the physical sensation of the breath in the body (wherever it's felt most easily, like the stomach or chest).\",
          \"durationMinutes\": 5,
          \"keyPoint\": \"Meditation isn't about clearing your mind. It's simply the gentle practice of paying attention to your breath, on purpose. Your mind *will* wander, and that's okay.\",
          \"tone\": \"Gentle, simple, and very reassuring.\"
        },
        {
          \"lessonNumber\": 2,
          \"title\": \"The Anchor of the Breath\",
          \"corePractice\": \"Using the breath as a reliable anchor to return to whenever the mind wanders.\",
          \"durationMinutes\": 6,
          \"keyPoint\": \"The breath is a stable anchor in the present moment you can always come back to amidst the storm of thoughts.\",
          \"tone\": \"Grounding, stable, encouraging.\"
        }
        // ... more lesson objects follow in sequence
      ]
    }
    ```

# EXECUTE
Based on the user's request for a new course, design the complete multi-lesson structure. Generate a single JSON object that contains the course metadata and the full, ordered array of lesson plans, ensuring the entire output is valid JSON and adheres perfectly to the specified structure."""
            ),
        ],
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")


if __name__ == "__main__":
    generate()
