from senda.domain.dtos.job import JobRecordDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import GenerationJob


class JobMapper(IModelMapper[GenerationJob, JobRecordDTO]):
    """Mapper for converting between GenerationJob model and JobRecordDTO."""

    @staticmethod
    def to_dto(model: GenerationJob) -> JobRecordDTO:
        return JobRecordDTO(
            id=model.id,
            job_type=model.job_type,
            course_id=model.course_id,
            lesson_id=model.lesson_id,
            status=model.status,
            payload=model.payload,
            result=model.result,
            error_message=model.error_message,
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_by=model.created_by,
        )

    @staticmethod
    def from_dto(dto: JobRecordDTO) -> GenerationJob:
        model = GenerationJob(
            job_type=dto.job_type,
            course_id=dto.course_id,
            lesson_id=dto.lesson_id,
            status=dto.status,
            payload=dto.payload,
            result=dto.result,
            error_message=dto.error_message,
            created_at=dto.created_at,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
            created_by=dto.created_by,
        )
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
