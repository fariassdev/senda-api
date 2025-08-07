#!/usr/bin/env python3
import requests
import time
import pyaudio
import json
from pathlib import Path

# 1. API ENDPOINT URL
KOKORO_API_URL = "http://localhost:8880/v1/audio/speech" 

# 2. MODEL PARAMETERS
# You can change the voice to: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
MODEL_VOICE = 'af_nicole'
MODEL_NAME = 'kokoro'  # Usually 'tts-1'

# Audio settings
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # Standard sampling rate for these models

# --- Meditation Flow ---
def load_meditation_flow():
    script_path = Path(__file__).parent / "default_meditation_script.json"
    with open(script_path, "r") as f:
        return json.load(f)

meditation_flow = load_meditation_flow()


def stream_and_play(text_to_speak):
    """
    Envía texto al endpoint estilo OpenAI y reproduce el audio en streaming.
    """
    p = pyaudio.PyAudio()
    stream = None

    payload = {
        "model": MODEL_NAME,
        "input": text_to_speak,
        "voice": MODEL_VOICE,
        "response_format": "pcm",
        "stream": True
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
        
        with requests.post(KOKORO_API_URL, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    stream.write(chunk)

    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if p:
            p.terminate()

print("Starting guided meditation...")

for action in meditation_flow:
    if action["type"] == "speak":
        sentence = action["content"]
        print(f"Speaking: '{sentence}'")
        stream_and_play(sentence)

    elif action["type"] == "pause":
        duration = action["duration"]
        print(f"--- Pausing for {duration} seconds ---")
        time.sleep(duration)

print("Meditation finished.")