#!/usr/bin/env python3
import requests
import json
from pathlib import Path
from pydub import AudioSegment
import io

# 1. API ENDPOINT URL
KOKORO_API_URL = "http://localhost:8880/v1/audio/speech"

# 2. MODEL PARAMETERS
# You can change the voice to: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
MODEL_VOICE = "af_nicole"
MODEL_NAME = "kokoro"  # Usually 'tts-1'

# Audio settings
RATE = 24000  # Standard sampling rate for these models
CHANNELS = 1
SAMPLE_WIDTH = 2  # 2 bytes for 16-bit PCM audio


# --- Meditation Flow ---
def load_meditation_flow():
    """Loads the meditation script from the JSON file."""
    script_path = Path(__file__).parent / "default_meditation_script.json"
    with open(script_path, "r") as f:
        return json.load(f)


def get_speech_audio(text_to_speak):
    """
    Sends text to the TTS API and returns the raw audio data.
    """
    payload = {
        "model": MODEL_NAME,
        "input": text_to_speak,
        "voice": MODEL_VOICE,
        "response_format": "pcm",
        "stream": True,
    }
    headers = {"Content-Type": "application/json"}
    audio_chunks = []

    try:
        print(f"Generating audio for: '{text_to_speak}'")
        with requests.post(
            KOKORO_API_URL, headers=headers, json=payload, stream=True
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    audio_chunks.append(chunk)
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None

    return b"".join(audio_chunks)


# --- Main Loop to Generate and Save the File ---
print("Starting meditation audio generation...")

meditation_flow = load_meditation_flow()
# Start with an empty audio segment
final_audio = AudioSegment.empty()

for action in meditation_flow:
    if action["type"] == "speak":
        speech_data = get_speech_audio(action["content"])
        if speech_data:
            # Create an AudioSegment from the raw PCM data
            speech_segment = AudioSegment.from_raw(
                io.BytesIO(speech_data),
                sample_width=SAMPLE_WIDTH,
                frame_rate=RATE,
                channels=CHANNELS,
            )
            final_audio += speech_segment

    elif action["type"] == "pause":
        duration_ms = action["duration"] * 1000  # pydub works in milliseconds
        print(f"--- Generating {action['duration']} seconds of silence ---")
        silence_segment = AudioSegment.silent(duration=duration_ms, frame_rate=RATE)
        final_audio += silence_segment

# Export the combined audio to an MP3 file
output_filename = "meditation_audio.mp3"
print(f"All audio generated. Saving to '{output_filename}'...")

final_audio.export(output_filename, format="mp3")

print(f"Meditation audio file saved successfully as '{output_filename}'.")
