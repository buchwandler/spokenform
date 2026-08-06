"""Optional document-language detection."""

from __future__ import annotations

from collections.abc import Callable, Collection

LanguageDetector = Callable[[str], str]


def lingua_detector(allowed_languages: Collection[str] | None = None) -> LanguageDetector:
    """Create a detector backed by the optional ``lingua`` package."""
    try:
        from lingua import Language, LanguageDetectorBuilder
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Language detection requires the 'langdetect' extra: "
            "python -m pip install 'spokenform[langdetect]'"
        ) from exc

    if allowed_languages:
        selected = []
        for code in allowed_languages:
            normalized = code.strip().lower().replace("_", "-").split("-", 1)[0]
            names = {
                "cs": "CZECH",
                "de": "GERMAN",
                "en": "ENGLISH",
                "es": "SPANISH",
                "fr": "FRENCH",
                "it": "ITALIAN",
                "pt": "PORTUGUESE",
            }
            try:
                language = Language.from_str(names[normalized])
            except KeyError as exc:
                supported = ", ".join(sorted(names))
                raise ValueError(
                    f"Unsupported detection language {code!r}. Supported languages: {supported}"
                ) from exc
            selected.append(language)
        builder = LanguageDetectorBuilder.from_languages(*selected)
    else:
        builder = LanguageDetectorBuilder.from_all_languages()
    detector = builder.build()

    def detect(text: str) -> str:
        language = detector.detect_language_of(text)
        if language is None:
            raise ValueError("Could not detect a language for the supplied text")
        return str(language.iso_code_639_1.name).lower()

    return detect
