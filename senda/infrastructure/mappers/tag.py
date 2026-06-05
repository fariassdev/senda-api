from senda.domain.dtos.tag import TagDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import Tag


class TagModelMapper(IModelMapper[Tag, TagDTO]):
    def to_dto(self, model: Tag) -> TagDTO:
        dto = TagDTO(id=model.id, tag=model.tag, created_at=model.created_at)
        return dto

    def from_dto(self, dto: TagDTO) -> Tag:
        model = Tag(tag=dto.tag)
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
