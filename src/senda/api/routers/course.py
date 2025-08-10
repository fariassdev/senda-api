from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from src.senda.api.schemas import course as schemas
from src.senda.api.core.database import get_db
from src.senda.api.repositories.course import CourseRepository, course_repository
from src.senda.api.services.course_architect import (
    CourseArchitect,
    GeminiCourseArchitect,
)
from src.senda.api.services.lesson_script_writer import (
    LessonScriptWriter,
    GeminiLessonScriptWriter,
)
from src.senda.api.services.lesson_service import LessonService

router = APIRouter()


# --- Dependency Injection for the Course Architect ---
def get_course_architect() -> CourseArchitect:
    """Dependency provider for the CourseArchitect service."""
    return GeminiCourseArchitect()


def get_lesson_script_writer() -> LessonScriptWriter:
    """Dependency provider for the LessonScriptWriter service."""
    return GeminiLessonScriptWriter()


def get_lesson_service(
    script_writer: LessonScriptWriter = Depends(get_lesson_script_writer),
    repo: CourseRepository = Depends(lambda: course_repository),
) -> LessonService:
    """Dependency provider for the LessonService."""
    return LessonService(script_writer, repo)


# In a real application, this would be a proper task queue (e.g., Celery)
_generating_courses = set()
_generating_lessons = set()


@router.post("/courses", response_model=schemas.Course, status_code=201)
def create_course_from_prompt(
    prompt_request: schemas.CourseCreatePrompt,
    db: Session = Depends(get_db),
    architect: CourseArchitect = Depends(get_course_architect),
):
    """
    Creates a new course draft from a text prompt by generating its structure with an AI architect.
    """
    try:
        # 1. Generate the course structure using the injected architect service
        course_structure = architect.generate_course_structure(prompt_request.prompt)

        # 2. Save the generated structure to the database
        db_course = course_repository.create_course(db, course_structure)
        return db_course
    except Exception as e:
        # A broad exception handler for issues during generation or DB saving
        raise HTTPException(status_code=500, detail=f"Failed to create course: {e}")


@router.get("/courses/{course_id}", response_model=schemas.Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = course_repository.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/courses/{course_id}", response_model=schemas.Course)
def update_course(
    course_id: int,
    course_update: schemas.CourseUpdate,
    db: Session = Depends(get_db),
):
    db_course = course_repository.get_course(db, course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if the course is being activated and if all lessons are generated
    if course_update.active and not db_course.active:
        ungenerated_lessons = course_repository.get_ungenerated_lessons(db, course_id)
        if ungenerated_lessons:
            raise HTTPException(
                status_code=400,
                detail="Cannot activate course: Not all lessons have been generated.",
            )

    return course_repository.update_course(db, db_course, course_update)


async def _generate_lesson_task(
    db: Session, course_id: int, lesson_id: int, lesson_service: LessonService
):
    try:
        lesson_service.generate_and_save_lesson_script(db, course_id, lesson_id)
    except Exception as e:
        print(f"Error generating script for lesson {lesson_id}: {e}")
        # Optionally, update lesson status to FAILED here if not handled in service


async def _generate_all_lessons_task(
    db: Session, course_id: int, lesson_service: LessonService
):
    try:
        lesson_service.generate_and_save_all_lesson_scripts(db, course_id)
    except Exception as e:
        print(f"Error generating scripts for course {course_id}: {e}")


@router.post("/courses/{course_id}/generate-all-scripts", status_code=202)
async def generate_all_lessons_scripts(
    course_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    if course_id in _generating_courses:
        raise HTTPException(
            status_code=409, detail="Course generation already in progress"
        )

    _generating_courses.add(course_id)
    background_tasks.add_task(_generate_all_lessons_task, db, course_id, lesson_service)
    return {
        "message": "Script generation for all lessons in course started in background"
    }


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/generate-script", status_code=202
)
async def generate_lesson_script(
    course_id: int,
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    lesson_service: LessonService = Depends(get_lesson_service),
):
    if (course_id, lesson_id) in _generating_lessons:
        raise HTTPException(
            status_code=409, detail="Lesson script generation already in progress"
        )

    _generating_lessons.add((course_id, lesson_id))
    background_tasks.add_task(
        _generate_lesson_task, db, course_id, lesson_id, lesson_service
    )
    return {"message": "Script generation for lesson started in background"}
