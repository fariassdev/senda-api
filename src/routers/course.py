from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from core.database import get_db
from repositories.lesson import LessonRepository
from repositories.course import CourseRepository
from schemas.course import CourseCreatePrompt, CourseUpdate, Course
from services.audio_service import AudioService
from services.course_architect import (
    CourseArchitect,
    GeminiCourseArchitect,
)
from services.lesson_script_writer import (
    LessonScriptWriter,
    GeminiLessonScriptWriter,
)
from services.lesson_script_service import LessonScriptService
from services.s3_service import S3Service

router = APIRouter(
    prefix="/courses",
    tags=["courses"],
)


def get_course_repository(db: Session = Depends(get_db)) -> CourseRepository:
    return CourseRepository(db)


def get_lesson_repository(db: Session = Depends(get_db)) -> LessonRepository:
    return LessonRepository(db)


def get_course_architect() -> CourseArchitect:
    """Dependency provider for the CourseArchitect service."""
    return GeminiCourseArchitect()


def get_lesson_script_writer() -> LessonScriptWriter:
    """Dependency provider for the LessonScriptWriter service."""
    return GeminiLessonScriptWriter()


def get_lesson_service(
    script_writer: LessonScriptWriter = Depends(get_lesson_script_writer),
    course_repository: CourseRepository = Depends(get_course_repository),
    lesson_repository: LessonRepository = Depends(get_lesson_repository),
) -> LessonScriptService:
    """Dependency provider for the LessonScriptService."""
    return LessonScriptService(script_writer, course_repository, lesson_repository)


def get_s3_service() -> S3Service:
    return S3Service()


def get_audio_service(s3_service: S3Service = Depends(get_s3_service)) -> AudioService:
    return AudioService(s3_service)


# In a real application, this would be a proper task queue (e.g., Celery)
_generating_courses = set()


@router.get("", response_model=list[Course])
def get_courses(
    skip: int = 0,
    limit: int = 10,
    course_repository: CourseRepository = Depends(get_course_repository),
):
    return course_repository.get_courses(skip=skip, limit=limit)


@router.post("", response_model=Course, status_code=201)
def create_course_from_prompt(
    prompt_request: CourseCreatePrompt,
    course_repository: CourseRepository = Depends(get_course_repository),
    architect: CourseArchitect = Depends(get_course_architect),
):
    """
    Creates a new course draft from a text prompt by generating its structure with an AI architect.
    """
    try:
        # 1. Generate the course structure using the injected architect service
        course_structure = architect.generate_course_structure(prompt_request.prompt)

        # 2. Save the generated structure to the database
        db_course = course_repository.create_course(course_structure)
        return db_course
    except Exception as e:
        # A broad exception handler for issues during generation or DB saving
        raise HTTPException(status_code=500, detail=f"Failed to create course: {e}")


@router.get("/{course_id}", response_model=Course)
def get_course(
    course_id: UUID,
    course_repository: CourseRepository = Depends(get_course_repository),
):
    course = course_repository.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=Course)
def update_course(
    course_id: UUID,
    course_update: CourseUpdate,
    course_repository: CourseRepository = Depends(get_course_repository),
):
    db_course = course_repository.get_course(course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if the course is being activated and if all lessons are READY_TO_PUBLISH
    if course_update.active and not db_course.active:
        if not course_repository.is_course_ready_to_publish(course_id):
            raise HTTPException(
                status_code=400,
                detail="Cannot activate course: Not all lessons are marked as READY_TO_PUBLISH.",
            )

    return course_repository.update_course(db_course, course_update)


async def _generate_all_lessons_task(
    course_id: UUID, lesson_service: LessonScriptService
):
    """Background task for generating all lesson scripts in a course."""
    try:
        lesson_service.generate_and_save_all_lesson_scripts(course_id)
    except Exception as e:
        print(f"Error generating scripts for course {course_id}: {e}")


@router.post("/{course_id}/generate-all-scripts", status_code=202)
async def generate_all_lessons_scripts(
    course_id: UUID,
    background_tasks: BackgroundTasks,
    lesson_service: LessonScriptService = Depends(get_lesson_service),
):
    if course_id in _generating_courses:
        raise HTTPException(
            status_code=409, detail="Course generation already in progress"
        )

    _generating_courses.add(course_id)
    background_tasks.add_task(_generate_all_lessons_task, course_id, lesson_service)
    return {
        "message": "Script generation for all lessons in course started in background"
    }


async def _generate_course_audios_task(
    course_id: UUID,
    audio_service: AudioService,
    course_repository: CourseRepository,
):
    """Background task for generating all audio files in a course."""
    try:
        audio_service.generate_course_audios(course_id, course_repository)
    except Exception as e:
        print(f"Error generating audios for course {course_id}: {e}")


@router.post("/{course_id}/generate-audios", status_code=202)
async def generate_course_audios(
    course_id: UUID,
    background_tasks: BackgroundTasks,
    audio_service: AudioService = Depends(get_audio_service),
    course_repository: CourseRepository = Depends(get_course_repository),
):
    background_tasks.add_task(
        _generate_course_audios_task, course_id, audio_service, course_repository
    )
    return {"message": "Audio generation for course started in background"}
