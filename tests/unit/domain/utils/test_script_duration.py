from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.utils.script_duration import estimate_script_duration_ms


class TestEstimateScriptDurationMs:
    def test_sums_reading_time_and_pauses(self) -> None:
        script_parts = [
            ScriptPartDTO(
                type=ScriptPartType.SPEAK,
                content="one two three four five six seven eight nine ten",
            ),
            ScriptPartDTO(type=ScriptPartType.PAUSE, duration=5.0),
        ]

        duration_ms = estimate_script_duration_ms(script_parts)

        # 10 words at 126 wpm ~= 5s + 5s pause
        assert duration_ms == 10_000

    def test_estimates_reading_time_for_longer_speech(self) -> None:
        script_parts = [
            ScriptPartDTO(
                type=ScriptPartType.SPEAK,
                content=" ".join(f"word{i}" for i in range(100)),
            )
        ]

        duration_ms = estimate_script_duration_ms(script_parts)

        # 100 words at 126 wpm ~= 48s
        assert duration_ms == 48_000

    def test_falls_back_to_target_duration_minutes(self) -> None:
        duration_ms = estimate_script_duration_ms([], target_duration_minutes=10)

        assert duration_ms == 600_000
