from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.exceptions import VoiceNotFoundException
from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.voice import IVoiceRepository
from senda.infrastructure.models import Voice


class VoiceRepository(IVoiceRepository):
    """Repository implementation for Voice model using SQLAlchemy."""

    def __init__(self, voice_mapper: IModelMapper[Voice, VoiceDTO]):
        self._voice_mapper = voice_mapper

    async def add(
        self,
        session: AsyncSession,
        create_item: CreateVoiceDTO,
        reference_s3_key: str,
        sample_s3_key: str,
    ) -> VoiceDTO:
        query = (
            insert(Voice)
            .values(
                name=create_item.name,
                slug=create_item.slug,
                description=create_item.description,
                language=create_item.language,
                gender=create_item.gender.value,
                reference_s3_key=reference_s3_key,
                sample_s3_key=sample_s3_key,
                tts_provider=create_item.tts_provider,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            .returning(Voice)
        )
        result = await session.execute(query)
        return self._voice_mapper.to_dto(result.scalar())

    async def get_or_none(
        self, session: AsyncSession, voice_id: UUID
    ) -> VoiceDTO | None:
        query = select(Voice).where(Voice.id == voice_id)
        if voice := await session.scalar(query):
            return self._voice_mapper.to_dto(voice)

    async def get(self, session: AsyncSession, voice_id: UUID) -> VoiceDTO:
        query = select(Voice).where(Voice.id == voice_id)
        if not (voice := await session.scalar(query)):
            raise VoiceNotFoundException()
        return self._voice_mapper.to_dto(voice)

    async def get_by_slug_or_none(
        self, session: AsyncSession, slug: str
    ) -> VoiceDTO | None:
        query = select(Voice).where(Voice.slug == slug)
        if voice := await session.scalar(query):
            return self._voice_mapper.to_dto(voice)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> VoiceDTO:
        query = select(Voice).where(Voice.slug == slug)
        if not (voice := await session.scalar(query)):
            raise VoiceNotFoundException()
        return self._voice_mapper.to_dto(voice)

    async def list_active(self, session: AsyncSession) -> list[VoiceDTO]:
        query = select(Voice).where(Voice.is_active).order_by(Voice.name)
        voices = await session.scalars(query)
        return [self._voice_mapper.to_dto(voice) for voice in voices]

    async def list_all(self, session: AsyncSession) -> list[VoiceDTO]:
        query = select(Voice).order_by(Voice.name)
        voices = await session.scalars(query)
        return [self._voice_mapper.to_dto(voice) for voice in voices]

    async def update(
        self, session: AsyncSession, voice_id: UUID, update_item: UpdateVoiceDTO
    ) -> VoiceDTO:
        query = (
            update(Voice)
            .where(Voice.id == voice_id)
            .values(updated_at=datetime.now())
            .returning(Voice)
        )

        if update_item.is_active is not None:
            query = query.values(is_active=update_item.is_active)
        if update_item.description is not None:
            query = query.values(description=update_item.description)
        if update_item.sample_s3_key is not None:
            query = query.values(sample_s3_key=update_item.sample_s3_key)

        result = await session.execute(query)
        return self._voice_mapper.to_dto(result.scalar())

    async def delete(self, session: AsyncSession, voice_id: UUID) -> None:
        query = delete(Voice).where(Voice.id == voice_id)
        await session.execute(query)
