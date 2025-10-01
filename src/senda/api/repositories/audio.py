from sqlalchemy.orm import Session
from src.senda.api.models.audio import Audio


class AudioRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_audio(self, audio_data: dict) -> Audio:
        """Create a new audio record with metrics"""
        audio = Audio(**audio_data)
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def get_audio_by_lesson_id(self, lesson_id: str) -> Audio | None:
        """Get audio record by lesson ID"""
        return self.db.query(Audio).filter(Audio.lesson_id == lesson_id).first()

    def update_audio(self, audio: Audio) -> Audio:
        """Update an existing audio record"""
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def delete_audio(self, audio_id: str) -> bool:
        """Delete an audio record"""
        audio = self.db.query(Audio).filter(Audio.id == audio_id).first()
        if audio:
            self.db.delete(audio)
            self.db.commit()
            return True
        return False
