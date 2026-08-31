"""Reusable, isolated abbreviation speech profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from abbr2words import AbbreviationEntry, Expander

from .language import normalize_language

GlossaryReadAs = Literal["long_form", "letters", "custom"]


class GlossaryConflictError(ValueError):
    """Raised when a profile contains ambiguous abbreviation surfaces."""

    def __init__(self, surfaces: tuple[str, ...], profile_name: str) -> None:
        self.surfaces = surfaces
        self.profile_name = profile_name
        details = ", ".join(repr(surface) for surface in surfaces)
        super().__init__(f"duplicate glossary surface {details} in profile {profile_name!r}")


def _validate_string(value: object, field: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{field} must not be empty or whitespace-only")
    return value


def _validate_guard(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string or None")
    try:
        re.compile(value)
    except re.error as error:
        raise ValueError(f"{field} must be a valid regular expression") from error
    return value


def _validate_string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field} must be a tuple of strings")
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{field} must contain only strings")
    return value


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    """One user-owned abbreviation and its desired speech realization."""

    abbreviation: str
    long_form: str
    read_as: GlossaryReadAs = "long_form"
    spoken_form: str | None = None
    aliases: tuple[str, ...] = ()
    description: str = ""
    case_sensitive: bool = False
    case_policy: Literal["fixed", "sentence"] = "fixed"
    only_if_preceded_by: str | None = None
    only_if_followed_by: str | None = None
    only_if_pos: tuple[str, ...] = ()
    not_if_pos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_string(self.abbreviation, "abbreviation", allow_empty=False)
        if self.abbreviation != self.abbreviation.strip():
            raise ValueError("abbreviation must not have leading or trailing whitespace")
        _validate_string(self.long_form, "long_form", allow_empty=False)
        if self.read_as not in {"long_form", "letters", "custom"}:
            raise ValueError("read_as must be 'long_form', 'letters', or 'custom'")
        if self.read_as == "custom":
            if not isinstance(self.spoken_form, str) or not self.spoken_form.strip():
                raise ValueError("read_as='custom' requires a non-empty spoken_form")
        elif self.spoken_form is not None:
            raise ValueError("spoken_form is only valid when read_as='custom'")
        aliases = _validate_string_tuple(self.aliases, "aliases")
        if any(not alias.strip() or alias != alias.strip() for alias in aliases):
            raise ValueError("aliases must not be empty or have leading/trailing whitespace")
        if self.abbreviation in aliases:
            raise ValueError("aliases must differ from abbreviation")
        if len(set(aliases)) != len(aliases):
            raise ValueError("aliases must not contain duplicates")
        _validate_string(self.description, "description")
        if type(self.case_sensitive) is not bool:
            raise TypeError("case_sensitive must be a bool")
        if self.case_policy not in {"fixed", "sentence"}:
            raise ValueError("case_policy must be 'fixed' or 'sentence'")
        _validate_guard(self.only_if_preceded_by, "only_if_preceded_by")
        _validate_guard(self.only_if_followed_by, "only_if_followed_by")
        _validate_string_tuple(self.only_if_pos, "only_if_pos")
        _validate_string_tuple(self.not_if_pos, "not_if_pos")


@dataclass(frozen=True, slots=True)
class SpeechProfile:
    """Immutable, reusable domain-specific speech configuration."""

    name: str
    language: str = "en"
    glossary: tuple[GlossaryEntry, ...] = ()

    def __post_init__(self) -> None:
        _validate_string(self.name, "name", allow_empty=False)
        normalized_language = normalize_language(self.language)
        object.__setattr__(self, "language", normalized_language)
        if not isinstance(self.glossary, tuple):
            raise TypeError("glossary must be a tuple of GlossaryEntry values")
        if any(not isinstance(entry, GlossaryEntry) for entry in self.glossary):
            raise TypeError("glossary must contain only GlossaryEntry values")

        surfaces: dict[str, str] = {}
        duplicates: list[str] = []
        for entry in self.glossary:
            for surface in (entry.abbreviation, *entry.aliases):
                key = surface.casefold()
                if key in surfaces:
                    duplicates.append(surface)
                else:
                    surfaces[key] = surface
        if duplicates:
            raise GlossaryConflictError(tuple(duplicates), self.name)


def profile_requires_registered_spelling(profile: SpeechProfile) -> bool:
    """Return whether a profile needs source spelling for a registered entry."""
    return any(entry.read_as == "letters" for entry in profile.glossary)


def _to_abbreviation_entry(entry: GlossaryEntry) -> AbbreviationEntry:
    speech_strategy = {
        "long_form": "expand",
        "letters": "spell_source",
        "custom": "custom",
    }[entry.read_as]
    return AbbreviationEntry(
        abbreviation=entry.abbreviation,
        expansion=entry.long_form,
        description=entry.description,
        case_sensitive=entry.case_sensitive,
        only_if_preceded_by=entry.only_if_preceded_by,
        only_if_followed_by=entry.only_if_followed_by,
        only_if_pos=entry.only_if_pos or None,
        not_if_pos=entry.not_if_pos or None,
        case_policy=entry.case_policy,
        speech_strategy=speech_strategy,
        spoken_form=entry.spoken_form,
        aliases=entry.aliases,
        origin="custom",
    )


@lru_cache(maxsize=64)
def get_compiled_profile_expander(
    profile: SpeechProfile,
    language: str,
    context: bool,
    initialism_mode: str,
    initialism_case: str,
    registered_initialism_mode: str,
) -> Expander:
    """Compile and cache one isolated dependency registry for a profile."""
    expander = Expander(
        language,
        context=context,
        initialism_mode=initialism_mode,
        initialism_case=initialism_case,
        registered_initialism_mode=registered_initialism_mode,
    )
    expander.add_many(
        (_to_abbreviation_entry(entry) for entry in profile.glossary),
        on_conflict="replace",
    )
    return expander


def clear_profile_cache() -> None:
    """Clear compiled profile registries for tests and process lifecycle control."""
    get_compiled_profile_expander.cache_clear()


__all__ = [
    "GlossaryConflictError",
    "GlossaryEntry",
    "GlossaryReadAs",
    "SpeechProfile",
    "clear_profile_cache",
    "get_compiled_profile_expander",
    "profile_requires_registered_spelling",
]
