from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from src.senda.api.schemas import course as schemas
from src.senda.api.repositories.course import course_repository
from src.senda.api.core.database import get_db
from src.senda.api.services.course_architect import CourseArchitect
from src.senda.api.services.gemini_course_architect import GeminiCourseArchitect

router = APIRouter()


# --- Dependency Injection for the Course Architect ---
def get_course_architect() -> CourseArchitect:
    """Dependency provider for the CourseArchitect service."""
    return GeminiCourseArchitect()


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


# ... (The rest of the endpoints for lesson generation remain the same for now)
# Note: They will need to be updated to use integer IDs.


async def _generate_lesson_task(db: Session, course_id: int, lesson_id: int):
    # ... (implementation needs to be updated to use int IDs)
    pass


async def _generate_all_lessons_task(db: Session, course_id: int):
    # ... (implementation needs to be updated to use int IDs)
    pass


@router.post("/courses/{course_id}/generate-all", status_code=202)
async def generate_all_lessons(
    course_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # ... (implementation needs to be updated to use int IDs)
    pass


@router.post("/courses/{course_id}/lessons/{lesson_id}/generate", status_code=202)
async def generate_lesson(
    course_id: int,
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # ... (implementation needs to be updated to use int IDs)
    pass
