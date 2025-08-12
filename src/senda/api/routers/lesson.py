from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.senda.api.core.database import get_db
from src.senda.api.repositories.lesson import LessonRepository
from src.senda.api.services.audio_service import AudioService
from src.senda.api.services.s3_service import S3Service

router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)


def get_lesson_repository(db: Session = Depends(get_db)) -> LessonRepository:
    return LessonRepository(db)


def get_s3_service() -> S3Service:
    return S3Service()


def get_audio_service(s3_service: S3Service = Depends(get_s3_service)) -> AudioService:
    return AudioService(s3_service)


@router.post("/{lesson_id}/generate-audio")
def generate_lesson_audio(
    lesson_id: int,
    lesson_repo: LessonRepository = Depends(get_lesson_repository),
    audio_service: AudioService = Depends(get_audio_service),
):
    lesson = lesson_repo.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    audio_url = audio_service.generate_and_upload_lesson_audio(lesson)

    if not audio_url:
        raise HTTPException(
            status_code=400, detail="Lesson has no script to generate audio from."
        )

    lesson.audio_url = audio_url
    lesson_repo.update_lesson(lesson)

    return {"message": "Audio generated successfully", "audio_url": audio_url}
