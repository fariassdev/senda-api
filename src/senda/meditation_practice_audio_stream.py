#!/usr/bin/env python3
import requests
import time
import pyaudio

# --- Configuración (Adaptada del ejemplo oficial) ---
# 1. URL DEL ENDPOINT ACTUALIZADA
KOKORO_API_URL = "http://localhost:8880/v1/audio/speech" 

# 2. PARÁMETROS DEL MODELO
# Puedes cambiar la voz a: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
MODEL_VOICE = 'af_nicole'
MODEL_NAME = 'kokoro' # Generalmente se deja como 'tts-1'

# Configuración de PyAudio para la reproducción
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000 # Frecuencia de muestreo estándar para estos modelos

# --- Flujo de la Meditación (Nuestra lógica de guión se mantiene) ---
# --- Meditation Flow: 5-Minute Guided Practice in English (Improved Flow) ---
meditation_flow = [
  {
    "type": "speak",
    "content": "Welcome to Senda. It's good to be here with you on the very first step of this path. Today, we begin a new journey, not by adding anything, but by simply discovering what's already here."
  },
  {
    "type": "speak",
    "content": "Our only goal today is to gently rest our attention on the breath. Meditation isn't about stopping your thoughts or feeling a certain way; it's just the practice of paying attention, on purpose. Your mind will wander, and that is a normal and expected part of the process. Let's begin."
  },
  {
    "type": "pause",
    "duration": 2.0
  },
  {
    "type": "speak",
    "content": "First, find a comfortable position, either sitting upright in a chair with your feet flat on the floor, or on a cushion. Allow your hands to rest easily in your lap and your back to be straight but not stiff."
  },
  {
    "type": "pause",
    "duration": 4.0
  },
  {
    "type": "speak",
    "content": "And when you're ready, gently close your eyes, or if you prefer, just lower your gaze and rest it softly on the floor in front of you."
  },
  {
    "type": "pause",
    "duration": 5.0
  },
  {
    "type": "speak",
    "content": "Take one slightly deeper breath in through the nose... and as you breathe out, just let go of any obvious tension you might be holding."
  },
  {
    "type": "pause",
    "duration": 5.0
  },
  {
    "type": "speak",
    "content": "Now, let your breath settle into its own natural, easy rhythm. No need to control it at all."
  },
  {
    "type": "pause",
    "duration": 8.0
  },
  {
    "type": "speak",
    "content": "Bring your awareness to the physical feeling of the breath in your body."
  },
  {
    "type": "pause",
    "duration": 5.0
  },
  {
    "type": "speak",
    "content": "You might notice it as the gentle rise and fall of your stomach."
  },
  {
    "type": "pause",
    "duration": 8.0
  },
  {
    "type": "speak",
    "content": "Or maybe you feel the slight expansion of your chest."
  },
  {
    "type": "pause",
    "duration": 8.0
  },
  {
    "type": "speak",
    "content": "Just choose whichever sensation is most clear to you, and gently rest your attention there."
  },
  {
    "type": "pause",
    "duration": 25.0
  },
  {
    "type": "speak",
    "content": "Simply noticing the feeling of one breath in..."
  },
  {
    "type": "pause",
    "duration": 5.0
  },
  {
    "type": "speak",
    "content": "...and the feeling of one breath out."
  },
  {
    "type": "pause",
    "duration": 30.0
  },
  {
    "type": "speak",
    "content": "Inevitably, you'll notice your mind has wandered away from the breath. This is not a mistake. It is the practice."
  },
  {
    "type": "pause",
    "duration": 4.0
  },
  {
    "type": "speak",
    "content": "The moment you realize you're thinking is a moment of awareness."
  },
  {
    "type": "pause",
    "duration": 4.0
  },
  {
    "type": "speak",
    "content": "With kindness, just acknowledge where your mind went, and then gently guide your focus back to the sensation of your next breath."
  },
  {
    "type": "pause",
    "duration": 30.0
  },
  {
    "type": "speak",
    "content": "Now, gently release your focus on the breath."
  },
  {
    "type": "pause",
    "duration": 3.0
  },
  {
    "type": "speak",
    "content": "For a few moments, just sit. Noticing the feeling of the air on your skin, the sounds around you, the state of your mind. Just being aware."
  },
  {
    "type": "pause",
    "duration": 10.0
  },
  {
    "type": "speak",
    "content": "When you feel ready, you can slowly and gently open your eyes, bringing your awareness back to the room."
  },
  {
    "type": "pause",
    "duration": 5.0
  },
  {
    "type": "speak",
    "content": "You have just completed the first practice. The goal was not perfection, but simply to begin. To show up, pay attention, and gently come back. You have done that."
  },
  {
    "type": "pause",
    "duration": 2.0
  },
  {
    "type": "speak",
    "content": "As this practice ends, the journey continues. Thank you for walking this first step of the path with me today."
  }
]

def stream_and_play(text_to_speak):
    """
    Envía texto al endpoint estilo OpenAI y reproduce el audio en streaming.
    """
    p = pyaudio.PyAudio()
    stream = None

    # 3. EL PAYLOAD SE ENVÍA COMO JSON EN UN POST
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
        
        # Se usa requests.post() con el payload JSON
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

# --- Bucle Principal (No cambia) ---
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