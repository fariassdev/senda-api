import io
import tempfile
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone

import requests
from pydub import AudioSegment

from models.lesson import Lesson, LessonStatus
from services.s3_service import S3Service
from services.event_publisher import EventPublisher
from repositories.course import CourseRepository

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

    def generate_lesson_audio(
        self,
        lesson: Lesson,
        lesson_repository,
    ) -> str | None:
        """Generate audio for a lesson, always emitting per-lesson events."""
        if not lesson.script or not isinstance(lesson.script, list):
            EventPublisher.publish_lesson_audio_failed(lesson.id, "No script available")
            return None

        EventPublisher.publish_lesson_audio_started(lesson.id)
        lesson.status = LessonStatus.AUDIO_GENERATING
        lesson_repository.update_lesson(lesson)

        try:
            audio_url = self.generate_and_upload_lesson_audio(lesson)
            if audio_url:
                lesson.audio_url = audio_url
                lesson.status = LessonStatus.AUDIO_COMPLETED
                lesson.audio_generated_at = datetime.now(timezone.utc)
                lesson_repository.update_lesson(lesson)

                EventPublisher.publish_lesson_audio_completed(lesson.id, audio_url)
                return audio_url
            else:
                lesson.status = LessonStatus.AUDIO_FAILED
                lesson_repository.update_lesson(lesson)

                EventPublisher.publish_lesson_audio_failed(
                    lesson.id, "No audio URL returned"
                )
                return None
        except Exception as e:
            lesson.status = LessonStatus.AUDIO_FAILED
            lesson_repository.update_lesson(lesson)

            EventPublisher.publish_lesson_audio_failed(lesson.id, str(e))
            raise

    def generate_course_audios(
        self, course_id: UUID, course_repository: CourseRepository
    ):
        """Generate audio for all lessons in a course, emitting only per-lesson events."""
        lessons = course_repository.get_lessons_by_course_id(course_id)

        if not lessons:
            print(f"No lessons found for course {course_id}")
            return

        for lesson in lessons:
            if lesson.script:
                try:
                    audio_url = self.generate_lesson_audio(lesson, course_repository)
                    if audio_url:
                        print(f"Audio generated for lesson {lesson.id}")
                    else:
                        print(
                            f"Audio generation failed for lesson {lesson.id}: No audio URL returned."
                        )
                except Exception as e:
                    print(f"Failed to generate audio for lesson {lesson.id}: {e}")
