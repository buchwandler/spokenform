"""Conservative Arabic Spokenform integration profile."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..config import NumberPolicy
from ..mapping import Replacement

_CITATION = re.compile(r"\[\d+\]")
NUMBER_POLICY = NumberPolicy.NONE


def iter_replacements(
    text: str,
    *,
    language: str = "ar",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Keep Arabic semantics conservative while preserving citation sanitation."""
    return tuple(
        Replacement(match.start(), match.end(), "", "structured", "ar", "ar.citation")
        for match in _CITATION.finditer(text)
    )


__all__ = ["NUMBER_POLICY", "iter_replacements"]
