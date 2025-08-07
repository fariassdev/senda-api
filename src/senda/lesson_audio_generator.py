#!/usr/bin/env python3
import requests
import json
from pathlib import Path
from pydub import AudioSegment
import io

# --- Configuration ---
KOKORO_API_URL = "http://localhost:8880/v1/audio/speech"
MODEL_VOICE = "af_nicole"
MODEL_NAME = "kokoro"
RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 2 bytes for 16-bit PCM audio


def get_speech_audio(text_to_speak):
    """Sends text to the TTS API and returns the raw audio data."""
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
        print(f"  - Generating audio for: '{text_to_speak[:50]}...'")
        with requests.post(
            KOKORO_API_URL, headers=headers, json=payload, stream=True
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    audio_chunks.append(chunk)
    except requests.exceptions.RequestException as e:
        print(f"    API Error: {e}")
        return None

    return b"".join(audio_chunks)


def generate_audio_from_script(meditation_script, output_path):
    """
    Generates an MP3 audio file from a meditation script.

    Args:
        meditation_script (list): A list of dictionaries representing the script.
        output_path (str or Path): The path to save the final MP3 file.
    """
    print(f"Starting audio generation for '{output_path}'...")
    final_audio = AudioSegment.empty()

    for action in meditation_script:
        if action["type"] == "speak":
            speech_data = get_speech_audio(action["content"])
            if speech_data:
                speech_segment = AudioSegment.from_raw(
                    io.BytesIO(speech_data),
                    sample_width=SAMPLE_WIDTH,
                    frame_rate=RATE,
                    channels=CHANNELS,
                )
                final_audio += speech_segment

        elif action["type"] == "pause":
            duration_ms = int(action["duration"] * 1000)
            print(f"  - Generating {action['duration']} seconds of silence.")
            silence_segment = AudioSegment.silent(duration=duration_ms, frame_rate=RATE)
            final_audio += silence_segment

    print(f"  -> Saving audio to '{output_path}'...")
    final_audio.export(output_path, format="mp3")
    print("Audio file saved successfully.")


if __name__ == "__main__":
    # Example usage for testing purposes
    print("Running audio generator in test mode...")

    # A default script for direct execution
    script_path = Path(__file__).parent / "default_meditation_script.json"
    with open(script_path, "r") as f:
        default_script = json.load(f)

    output_file = "test_meditation_audio.mp3"

    generate_audio_from_script(default_script, output_file)
