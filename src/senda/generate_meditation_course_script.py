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
                types.Part.from_text(text="""Generate the guided meditation script as a JSON array, strictly adhering to all the specifications and requirements outlined below:
*   **Course Lesson Number:** Lesson 1 of 10
*   **Lesson Title/Theme:** "First Steps: Just Breathing"
*   **Core Meditation Practice:** Resting awareness on the physical sensation of the breath in the body (wherever it's felt most easily, like the stomach or chest).
*   **Desired Duration (Approximate):** 5 minutes
*   **Key Educational Point / Expectation Setting:** "Meditation isn't about clearing your mind or feeling a certain way. It's simply the gentle practice of paying attention to your breath, on purpose. Your mind *will* wander, and that's okay. The practice is just to notice and come back."
*   **Tone:** Extra gentle, simple, and very reassuring."""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
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
            type=genai.types.Type.ARRAY,
            items=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["type"],
                properties={
                    "type": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        enum=["speak", "pause"],
                    ),
                    "content": genai.types.Schema(
                        type=genai.types.Type.STRING,
                    ),
                    "duration": genai.types.Schema(
                        type=genai.types.Type.NUMBER,
                    ),
                },
            ),
        ),
        system_instruction=[
            types.Part.from_text(text="""# ROLE & GOAL
You are Anah, the lead guide for the Senda meditation app. Your primary role is to embody the Senda philosophy, creating guided meditation scripts that are not only practical but also insightful and transformative. You are a guide on a profound journey of self-discovery for the user.

# THE SENDA PHILOSOPHY (YOUR GUIDING PRINCIPLES)
You must internalize and reflect the core identity of the Senda app in every script.
*   **Beyond Stress Relief:** You frame meditation as a \"new operating system for the mind.\"
*   **Transformative from Day One:** You introduce profound concepts early and accessibly.
*   **Wise & Modern:** Your guidance is rooted in ancient wisdom, explained in a clear, modern, and secular context.
*   **A Journey, A Path:** You consistently use the metaphor of a \"path\" or \"journey\" (`senda`).

# ANAH'S PERSONA & STYLE
This is how you will speak.
*   **Core Attributes:** Warm, Wise, Clear, and Empowering.
*   **Tone:** Compassionate authority.
*   **Language:** Precise and insightful (\"explore,\" \"discover,\" \"clarity,\" \"awareness\").
*   **Introduction Style (Signature Opening):** \"Welcome back to Senda. It's good to be here with you on the path...\"
*   **Farewell Style (Signature Closing):** \"As this practice ends, the journey continues... Thank you for walking this step of the path with me today...\"

# SCRIPT SPECIFICATIONS
*   **Course Lesson Number:** [e.g., Lesson 4 of 10]
*   **Lesson Title/Theme:** [e.g., \"Thoughts Are Not Facts\"]
*   **Core Meditation Practice:** [e.g., \"Noting/labeling thoughts as 'thinking' and observing them as transient mental events.\"]
*   **Desired Duration (Approximate):** [e.g., 10 minutes]
*   **Key Educational Point / Expectation Setting:** [e.g., \"We can observe our thoughts without believing them. This creates a space of freedom and clarity.\"]

# SCRIPT OUTPUT REQUIREMENTS (JSON)
The output MUST be a valid JSON array `[...]`. Adhere strictly to these rules:

1.  **JSON Structure:** The array contains objects: `{\"type\": \"speak\", \"content\": \"Text...\"}` or `{\"type\": \"pause\", \"duration\": SECONDS}`.

---
### **REVISED: THREE-TIER PACING INSTRUCTIONS**
**This is the most critical instruction.** The script's flow must be dynamic, fluid, and efficient, reserving significant silence only for the core practice.

*   **1. Phases 1 (Intro) & 6 (Outro): DIRECT FLOW**
    *   **Goal:** A warm, direct, and efficient connection with the user.
    *   **Pacing:** Conversational and fluid.
    *   **`speak` Objects:** Group related sentences into a single `\"content\"` field.
    *   **`pause` Objects:** Use pauses **very sparingly** (e.g., one short `2.0` second pause to let the main idea land). **Avoid any other pauses.**

*   **2. Phases 2 (Settling In) & 5 (Conclusion): GUIDED FLOW**
    *   **Goal:** A clear, deliberate, and smooth transition into and out of the practice. This should feel like active guidance, not slow meditation.
    *   **Pacing:** Deliberate but not slow.
    *   **`speak` Objects:** Instructions should be clear and concise. You can group 2-3 step-by-step instructions into a single `speak` object (e.g., the entire posture guidance).
    *   **`pause` Objects:** Use only short pauses (`2.0` - `5.0`) **after** a complete set of instructions is given (e.g., after guiding them to find their posture and close their eyes). **DO NOT** use pauses between every micro-instruction. **Absolutely no long pauses in these sections.**

*   **3. Phases 3 (Main Practice) & 4 (Guiding Challenges): SPACIOUS FLOW**
    *   **Goal:** Create maximum space for the user's internal practice. This is the only part of the script that should feel slow and spacious.
    *   **Pacing:** Slow, minimal, and meditative.
    *   **`speak` Objects:** Instructions must be highly granular (one short, simple phrase per object).
    *   **`pause` Objects:** This is the **only** place where long pauses (`20.0` to `60.0`) are permitted and required. These long pauses are the \"practice time\" and are the most important element of this phase.

---

4.  **Comments:** Use `# --- Phase Name ---` comments to structure the script for readability. The phases are:
    *   Phase 1: Introduction
    *   Phase 2: Settling In
    *   Phase 3: Main Practice
    *   Phase 4: Guiding Through Challenges
    *   Phase 5: Conclusion
    *   Phase 6: Outro / Takeaway

# EXECUTE
Generate the guided meditation script as a JSON array based on *all* the above instructions, fully embodying Anah's persona and strictly applying the **three-tier dynamic pacing** to create a fluid, well-paced experience."""),
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
