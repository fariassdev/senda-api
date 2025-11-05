"""Utility for loading prompt files from disk."""

from pathlib import Path


class PromptLoader:
    """Loads prompt templates from the filesystem."""

    def __init__(self, base_path: str | None = None):
        """
        Initialize the prompt loader.

        Args:
            base_path: Optional base path for prompts. Defaults to workspace root.
        """
        self._base_path = Path(base_path) if base_path else Path.cwd()

    def load_prompt(self, relative_path: str) -> str:
        """
        Load a prompt template from a file.

        Args:
            relative_path: Path to the prompt file relative to base_path

        Returns:
            The prompt content as a string

        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        prompt_file = self._base_path / relative_path
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        return prompt_file.read_text(encoding="utf-8")
