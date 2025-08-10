from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from src.senda.api.schemas import course as schemas
from src.senda.api.repositories.course import course_repository
from src.senda.api.core.database import get_db
from src.senda.api.models.course import LessonStatus

router = APIRouter()

# In a real application, this would be a proper task queue (e.g., Celery)
# For now, a simple in-memory set to track ongoing generations
_generating_courses = set()
_generating_lessons = set()


async def _generate_lesson_task(db: Session, course_id: str, lesson_id: int):
    try:
        lesson = course_repository.get_lesson(db, course_id, lesson_id)
        if not lesson:
            return

        # Simulate script generation
        script_url = f"/generated_courses/{course_id}/lesson_{lesson_id}_script.json"
        # Simulate audio generation
        audio_url = f"/generated_courses/{course_id}/lesson_{lesson_id}_audio.mp3"

        course_repository.update_lesson_status(
            db, lesson, LessonStatus.COMPLETED, script_url, audio_url
        )
    except Exception as e:
        lesson = course_repository.get_lesson(db, course_id, lesson_id)
        if lesson:
            course_repository.update_lesson_status(db, lesson, LessonStatus.FAILED)
        print(f"Error generating lesson {lesson_id} for course {course_id}: {e}")
    finally:
        _generating_lessons.discard((course_id, lesson_id))


async def _generate_all_lessons_task(db: Session, course_id: str):
    try:
        course = course_repository.get_course(db, course_id)
        if not course:
            return

        lessons_to_generate = course_repository.get_ungenerated_lessons(db, course_id)
        for lesson in lessons_to_generate:
            if (course_id, lesson.id) not in _generating_lessons:
                _generating_lessons.add((course_id, lesson.id))
                course_repository.update_lesson_status(
                    db, lesson, LessonStatus.GENERATING
                )
                # In a real app, this would dispatch to a background worker
                await _generate_lesson_task(
                    db, course_id, lesson.id
                )  # Directly call for simulation

    except Exception as e:
        print(f"Error generating all lessons for course {course_id}: {e}")
    finally:
        _generating_courses.discard(course_id)


@router.post("/courses", response_model=schemas.Course, status_code=201)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    db_course = course_repository.get_course(db, course.id)
    if db_course:
        raise HTTPException(
            status_code=400, detail="Course with this ID already exists"
        )
    return course_repository.create_course(db, course)


@router.get("/courses/{course_id}", response_model=schemas.Course)
def get_course(course_id: str, db: Session = Depends(get_db)):
    course = course_repository.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/courses/{course_id}/generate-all", status_code=202)
async def generate_all_lessons(
    course_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    course = course_repository.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course_id in _generating_courses:
        raise HTTPException(
            status_code=409, detail="Generation for this course is already in progress."
        )

    _generating_courses.add(course_id)
    background_tasks.add_task(_generate_all_lessons_task, db, course_id)
    return {"message": "Generation process started for all eligible lessons."}


@router.post("/courses/{course_id}/lessons/{lesson_id}/generate", status_code=202)
async def generate_lesson(
    course_id: str,
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    lesson = course_repository.get_lesson(db, course_id, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found in this course.")

    if (course_id, lesson_id) in _generating_lessons:
        raise HTTPException(
            status_code=409, detail="Lesson generation already in progress."
        )

    _generating_lessons.add((course_id, lesson_id))
    course_repository.update_lesson_status(db, lesson, LessonStatus.GENERATING)
    background_tasks.add_task(_generate_lesson_task, db, course_id, lesson_id)
    return {"message": "Lesson generation started."}
