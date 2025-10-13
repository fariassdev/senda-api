from abc import ABC, abstractmethod
from schemas.course import CourseCreate


class CourseArchitect(ABC):
    """
    Abstract base class for a course architect.
    It defines the contract for generating a course structure from a prompt.
    """

    @abstractmethod
    def generate_course_structure(self, prompt: str) -> CourseCreate:
        """
        Generates the structure of a course based on a given prompt.

        Args:
            prompt: The input prompt describing the desired course.

        Returns:
            A CourseCreate schema object representing the generated course structure.
        """
        pass
