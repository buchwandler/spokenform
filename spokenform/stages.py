"""Small helpers shared by the explicit preparation stages."""

from __future__ import annotations

from collections.abc import Callable

from .models import PreparationStage, make_stage


def apply_stage(
    stages: list[PreparationStage],
    name: str,
    text: str,
    transform: Callable[[str], str],
    restore: Callable[[str], str] | None = None,
) -> str:
    """Apply one deterministic stage and retain its before/after provenance."""
    after = transform(text)
    restore_text = restore or (lambda value: value)
    stages.append(make_stage(name, restore_text(text), restore_text(after)))
    return after


__all__ = ["apply_stage"]
