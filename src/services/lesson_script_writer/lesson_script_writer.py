from abc import ABC, abstractmethod

from schemas.lesson import ScriptPart


class LessonScriptWriter(ABC):
    """
    Abstract base class for a lesson script writer.
    It defines the contract for generating a meditation script for a lesson.
    """

    @abstractmethod
    def generate_script(
        self, course_context: dict[str, any], lesson_details: dict[str, any]
    ) -> list[ScriptPart]:
        """
        Generates a meditation script for a specific lesson within a course.

        Args:
            course_context (Dict[str, Any]): A dictionary containing the course name, description, and total lessons.
            lesson_details (Dict[str, Any]): A dictionary containing the details for the specific lesson.

        Returns:
            list[ScriptPart]: A list of dictionaries representing the generated meditation script.
                                   Each dictionary should have 'type', 'content', and optionally 'duration'.
        """
        pass
