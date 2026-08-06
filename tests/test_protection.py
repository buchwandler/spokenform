import pytest

from spokenform import PreparationConfig, ProtectionError, prepare


def test_config_and_caller_protected_span() -> None:
    result = prepare(
        "Dr. 12 https://example.org/a2",
        config=PreparationConfig(language="en"),
        protected_spans=[(0, 3)],
    )
    assert result.spoken_text.startswith("Dr.")
    assert "twelve" in result.spoken_text
    assert "https://example.org/a2" in result.spoken_text
    assert result.warnings == ()


def test_invalid_protection_warns_or_raises() -> None:
    result = prepare("123", protected_spans=[(-1, 2)])
    assert result.warnings[0].startswith("[PROTECT]")

    with pytest.raises(ProtectionError):
        prepare("123", protected_spans=[(-1, 2)], strict=True)


def test_overlapping_protection_warns_or_raises() -> None:
    result = prepare("123", protected_spans=[(0, 2), (1, 3)])
    assert any("overlapping" in warning for warning in result.warnings)

    with pytest.raises(ProtectionError):
        prepare("123", protected_spans=[(0, 2), (1, 3)], strict=True)
