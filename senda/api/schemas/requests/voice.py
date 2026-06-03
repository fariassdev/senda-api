from typing import Literal

from fastapi import Form
from pydantic import BaseModel, Field

from senda.domain.dtos.voice import CreateVoiceDTO, GenderEnum, UpdateVoiceDTO


class CreateVoiceData(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    gender: str = Field(...)  # 'female' | 'male' | 'neutral'
    language: str = Field(default="es")
    tts_provider: Literal["chatterbox"] = Field(default="chatterbox")
    description: str | None = Field(default=None)


class CreateVoiceRequest(BaseModel):
    voice: CreateVoiceData

    def to_dto(self) -> CreateVoiceDTO:
        return CreateVoiceDTO(
            name=self.voice.name,
            slug=self.voice.slug,
            gender=GenderEnum(self.voice.gender),
            language=self.voice.language,
            tts_provider=self.voice.tts_provider,
            description=self.voice.description,
        )

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        slug: str = Form(...),
        gender: str = Form(...),
        language: str = Form("es"),
        tts_provider: Literal["chatterbox"] = Form("chatterbox"),
        description: str | None = Form(None),
    ) -> "CreateVoiceRequest":
        return cls(
            voice=CreateVoiceData(
                name=name,
                slug=slug,
                gender=gender,
                language=language,
                tts_provider=tts_provider,
                description=description,
            )
        )


class UpdateVoiceData(BaseModel):
    tts_provider: str | None = Field(None)
    is_active: bool | None = Field(None)
    description: str | None = Field(None)


class UpdateVoiceRequest(BaseModel):
    voice: UpdateVoiceData

    def to_dto(self) -> UpdateVoiceDTO:
        return UpdateVoiceDTO(
            tts_provider=self.voice.tts_provider,
            is_active=self.voice.is_active,
            description=self.voice.description,
        )
