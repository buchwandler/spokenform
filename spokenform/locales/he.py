"""Conservative Hebrew Spokenform integration profile."""

from __future__ import annotations

from collections.abc import Iterable

from ..config import NumberPolicy
from ..mapping import Replacement

NUMBER_POLICY = NumberPolicy.NONE


def iter_replacements(
    text: str,
    *,
    language: str = "he",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Keep Hebrew semantic structures caller-managed for the first profile release."""
    return ()


__all__ = ["NUMBER_POLICY", "iter_replacements"]
