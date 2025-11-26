"""Configuration for Gemini AI provider."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
    """Configuration for Gemini API integration."""

    api_key: str
    model: str = "gemini-2.5-flash"
    thinking_budget: int = 10000
