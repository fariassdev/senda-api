from fastapi import Form
from pydantic import BaseModel, Field

from senda.domain.dtos.voice import CreateVoiceDTO, GenderEnum, UpdateVoiceDTO


class CreateVoiceData(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    gender: str = Field(...)  # 'female' | 'male' | 'neutral'
    language: str = Field(default="es")
    exaggeration: float = Field(default=0.3, ge=0.0, le=2.0)
    cfg_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    temperature: float = Field(default=0.4, ge=0.1, le=1.0)
    description: str | None = Field(default=None)


class CreateVoiceRequest(BaseModel):
    voice: CreateVoiceData

    def to_dto(self) -> CreateVoiceDTO:
        return CreateVoiceDTO(
            name=self.voice.name,
            slug=self.voice.slug,
            gender=GenderEnum(self.voice.gender),
            language=self.voice.language,
            exaggeration=self.voice.exaggeration,
            cfg_weight=self.voice.cfg_weight,
            temperature=self.voice.temperature,
            description=self.voice.description,
        )

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        slug: str = Form(...),
        gender: str = Form(...),
        language: str = Form("es"),
        exaggeration: float = Form(0.3),
        cfg_weight: float = Form(0.5),
        temperature: float = Form(0.4),
        description: str | None = Form(None),
    ) -> "CreateVoiceRequest":
        return cls(
            voice=CreateVoiceData(
                name=name,
                slug=slug,
                gender=gender,
                language=language,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                temperature=temperature,
                description=description,
            )
        )


class UpdateVoiceData(BaseModel):
    exaggeration: float | None = Field(None, ge=0.0, le=2.0)
    cfg_weight: float | None = Field(None, ge=0.0, le=1.0)
    temperature: float | None = Field(None, ge=0.1, le=1.0)
    is_active: bool | None = Field(None)
    description: str | None = Field(None)


class UpdateVoiceRequest(BaseModel):
    voice: UpdateVoiceData

    def to_dto(self) -> UpdateVoiceDTO:
        return UpdateVoiceDTO(
            exaggeration=self.voice.exaggeration,
            cfg_weight=self.voice.cfg_weight,
            temperature=self.voice.temperature,
            is_active=self.voice.is_active,
            description=self.voice.description,
        )
