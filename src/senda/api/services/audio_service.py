import io
import tempfile
from pathlib import Path

import requests
from pydub import AudioSegment

from src.senda.api.models.course import Lesson
from src.senda.api.services.s3_service import S3Service

KOKORO_API_URL = "http://localhost:8880/v1/audio/speech"
MODEL_VOICE = "af_nicole"
MODEL_NAME = "kokoro"
RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2


class AudioService:
    def __init__(self, s3_service: S3Service):
        self.s3_service = s3_service

    def _get_speech_audio(self, text_to_speak: str):
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

    def generate_and_upload_lesson_audio(self, lesson: Lesson) -> str | None:
        if not lesson.script or not isinstance(lesson.script, list):
            return None

        final_audio = AudioSegment.empty()

        for action in lesson.script:
            if action.get("type") == "speak":
                speech_data = self._get_speech_audio(action.get("content", ""))
                if speech_data:
                    speech_segment = AudioSegment.from_raw(
                        io.BytesIO(speech_data),
                        sample_width=SAMPLE_WIDTH,
                        frame_rate=RATE,
                        channels=CHANNELS,
                    )
                    final_audio += speech_segment

            elif action.get("type") == "pause":
                duration_ms = int(action.get("duration", 0) * 1000)
                silence_segment = AudioSegment.silent(
                    duration=duration_ms, frame_rate=RATE
                )
                final_audio += silence_segment

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            final_audio.export(tmp_file.name, format="mp3")

            random_string = self.s3_service.generate_s3_safe_random_string_random()
            object_name = f"audio/{lesson.id}_{lesson.title.replace(' ', '_')}_{random_string}.mp3"
            s3_url = self.s3_service.upload_file(
                file_path=tmp_file.name,
                object_name=object_name,
            )

        Path(tmp_file.name).unlink()

        return s3_url
