"""Pinned PolyNorm-Bench data discovery, download, and parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

POLYNORM_REPOSITORY = "https://github.com/apple/ml-speech-polynorm-bench"
POLYNORM_RAW_BASE = "https://raw.githubusercontent.com/apple/ml-speech-polynorm-bench"
POLYNORM_COMMIT = "f3c67e047bea6b7c40bc2466c0fdaad51d8ce67d"
POLYNORM_LICENSE = "CC BY-NC-ND 4.0"
POLYNORM_LOCALES = ("de-DE", "en-US", "es-MX", "fr-FR", "it-IT")
POLYNORM_TO_SPOKENFORM = {
    "de-DE": "de",
    "en-US": "en",
    "es-MX": "es",
    "fr-FR": "fr",
    "it-IT": "it",
}


@dataclass(frozen=True, slots=True)
class PolyNormCase:
    """One upstream PolyNorm normalization case."""

    polynorm_locale: str
    index: str
    category: str
    original_text: str
    normalized_text: str

    @property
    def case_id(self) -> str:
        return f"{self.polynorm_locale}:{self.index}"

    @classmethod
    def from_dict(cls, locale: str, payload: dict[str, object]) -> PolyNormCase:
        required = ("index", "category", "original_text", "normalized_text")
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"PolyNorm case missing fields: {', '.join(missing)}")
        values = {key: payload[key] for key in required}
        if not all(isinstance(value, (str, int, float)) for value in values.values()):
            raise ValueError(f"PolyNorm case has invalid fields: {payload!r}")
        return cls(
            polynorm_locale=locale,
            index=str(values["index"]),
            category=str(values["category"]),
            original_text=str(values["original_text"]),
            normalized_text=str(values["normalized_text"]),
        )


def cache_path(cache_dir: Path | str = ".cache/polynorm-bench") -> Path:
    """Return the commit-scoped cache directory."""
    return Path(cache_dir) / POLYNORM_COMMIT


def data_path(locale: str, cache_dir: Path | str = ".cache/polynorm-bench") -> Path:
    """Return the cached JSONL path for one supported locale."""
    if locale not in POLYNORM_TO_SPOKENFORM:
        raise ValueError(f"Unsupported PolyNorm overlap locale: {locale}")
    return cache_path(cache_dir) / locale / f"{locale}_groundtruth.jsonl"


def _raw_url(path: str) -> str:
    return f"{POLYNORM_RAW_BASE}/{POLYNORM_COMMIT}/{path}"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=60) as response:  # noqa: S310 - pinned public HTTPS URL
        destination.write_bytes(response.read())


def ensure_data(
    locales: tuple[str, ...],
    *,
    cache_dir: Path | str = ".cache/polynorm-bench",
    offline: bool = False,
    accept_license: bool = False,
    refresh: bool = False,
) -> Path:
    """Ensure selected locale files and the upstream license exist locally."""
    root = cache_path(cache_dir)
    missing = [locale for locale in locales if refresh or not data_path(locale, cache_dir).is_file()]
    license_path = root / "LICENSE"
    if (missing or not license_path.is_file()) and offline:
        absent = ", ".join(missing) or "LICENSE"
        raise FileNotFoundError(f"Offline PolyNorm cache is missing: {absent}")
    if missing or not license_path.is_file():
        if not accept_license:
            raise PermissionError(
                "PolyNorm data is CC BY-NC-ND 4.0; pass --accept-license before downloading."
            )
        if not license_path.is_file() or refresh:
            _download(_raw_url("LICENSE"), license_path)
        for locale in missing:
            _download(_raw_url(f"polynorm_bench/{locale}/{locale}_groundtruth.jsonl"), data_path(locale, cache_dir))
    return root


def load_cases(
    locales: tuple[str, ...],
    *,
    cache_dir: Path | str = ".cache/polynorm-bench",
    category: str | None = None,
    case_id: str | None = None,
    limit: int | None = None,
) -> tuple[PolyNormCase, ...]:
    """Load, filter, and deterministically order cached cases."""
    selected: list[PolyNormCase] = []
    for locale in locales:
        path = data_path(locale, cache_dir)
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc
                if not isinstance(payload, dict):
                    raise ValueError(f"PolyNorm case is not an object in {path}:{line_number}")
                case = PolyNormCase.from_dict(locale, payload)
                if category is not None and case.category.casefold() != category.casefold():
                    continue
                if case_id is not None and case.case_id != case_id:
                    continue
                selected.append(case)
    selected.sort(key=lambda case: (case.polynorm_locale, int(case.index) if case.index.isdigit() else case.index))
    return tuple(selected[:limit] if limit is not None else selected)


def selected_locales(locale: str | None = None) -> tuple[str, ...]:
    """Return all overlap locales or one validated locale."""
    if locale is None:
        return POLYNORM_LOCALES
    if locale not in POLYNORM_TO_SPOKENFORM:
        raise ValueError(f"Unsupported PolyNorm overlap locale: {locale}")
    return (locale,)


__all__ = [
    "POLYNORM_COMMIT",
    "POLYNORM_LICENSE",
    "POLYNORM_LOCALES",
    "POLYNORM_RAW_BASE",
    "POLYNORM_REPOSITORY",
    "POLYNORM_TO_SPOKENFORM",
    "PolyNormCase",
    "cache_path",
    "data_path",
    "ensure_data",
    "load_cases",
    "selected_locales",
]
