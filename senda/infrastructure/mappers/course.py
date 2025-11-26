from senda.domain.dtos.course import CourseRecordDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import Course


class CourseModelMapper(IModelMapper[Course, CourseRecordDTO]):
    @staticmethod
    def to_dto(model: Course) -> CourseRecordDTO:
        dto = CourseRecordDTO(
            id=model.id,
            author_id=model.author_id,
            slug=model.slug,
            title=model.title,
            description=model.description,
            difficulty_level=model.difficulty_level,
            active=model.active,
            image_placeholder_url=model.image_placeholder_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        return dto

    @staticmethod
    def from_dto(dto: CourseRecordDTO) -> Course:
        model = Course(
            author_id=dto.author_id,
            slug=dto.slug,
            title=dto.title,
            description=dto.description,
            difficulty_level=dto.difficulty_level,
            active=dto.active,
            image_placeholder_url=dto.image_placeholder_url,
            created_at=dto.created_at,
        )
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
