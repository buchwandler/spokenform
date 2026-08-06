"""Optional spaCy model loading without making spaCy a core import."""

from __future__ import annotations

from threading import RLock
from typing import Any


class SpacyModelError(RuntimeError):
    """Raised when an explicitly requested spaCy model is unavailable."""


_CACHE: dict[tuple[str | None, str], Any] = {}
_LOCK = RLock()


def load_spacy_model(model: str | None, *, language: str | None = None) -> Any:
    """Load and cache a named model; never download one implicitly."""
    if not isinstance(model, str) or not model.strip():
        raise SpacyModelError(
            "spaCy was requested without a model name; pass spacy_model='en_core_web_sm'"
        )
    if language is not None and not isinstance(language, str):
        raise TypeError("language must be a string or None")
    expected_language = (
        language.lower().replace("_", "-").split("-", 1)[0]
        if language and language.strip()
        else None
    )
    key = (expected_language, model)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    try:
        import spacy
    except ImportError as exc:
        raise SpacyModelError(
            "spaCy support requires the 'spacy' extra: python -m pip install 'spokenform[spacy]'"
        ) from exc
    try:
        pipeline = spacy.load(model)
    except Exception as exc:
        raise SpacyModelError(
            f"Requested spaCy model {model!r} is unavailable; install it explicitly "
            "and do not rely on automatic downloads"
        ) from exc

    pipeline_language = getattr(pipeline, "lang", None)
    actual_language = (
        str(pipeline_language).lower().replace("_", "-").split("-", 1)[0]
        if pipeline_language
        else None
    )
    if expected_language and actual_language not in {None, expected_language, "xx"}:
        raise SpacyModelError(
            f"Requested spaCy model {model!r} uses language {actual_language!r}, "
            f"not {expected_language!r}"
        )

    with _LOCK:
        _CACHE[key] = pipeline
    return pipeline


def reset_spacy_cache() -> None:
    """Clear models loaded by spokenform."""
    with _LOCK:
        _CACHE.clear()


__all__ = ["SpacyModelError", "load_spacy_model", "reset_spacy_cache"]
