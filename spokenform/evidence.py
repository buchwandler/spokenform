"""Provider-neutral lexical and semantic evidence integration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .language import base_language, normalize_language


class LexicalSegmentEvidence(Protocol):
    """Evidence for one segment returned by a lexical segmenter."""

    text: str
    known: bool
    frequency_rank: int | None


class WordEvidence(Protocol):
    """Lexical and orthographic evidence for one word."""

    text: str
    known: bool
    frequency_rank: int | None
    frequency_count: int | None
    has_lowercase: bool
    has_titlecase: bool
    has_uppercase: bool


class ContextCueEvidence(Protocol):
    """One contextual cue contributing to a semantic domain result."""

    text: str
    start: int
    end: int
    distance: int
    weight: float


class DomainEvidence(Protocol):
    """Positive semantic evidence for a target span."""

    score: float
    cues: Sequence[ContextCueEvidence]


class LexicalEvidenceProvider(Protocol):
    """Minimal provider contract consumed by Spokenform."""

    language: str
    capabilities: tuple[str, ...]

    def word(self, word: str) -> WordEvidence: ...

    def segment(
        self,
        text: str,
        *,
        max_word_length: int = 32,
    ) -> tuple[LexicalSegmentEvidence, ...]: ...

    def supports_domain(
        self,
        text: str,
        *,
        target: tuple[int, int],
        domain: str,
        window: int = 6,
        decay: float = 0.7,
        threshold: float = 0.4,
    ) -> DomainEvidence | None: ...


@dataclass(frozen=True, slots=True)
class EvidenceDetails:
    """Stable diagnostic details extracted from one provider result."""

    source: str
    score: float | None = None
    cues: tuple[str, ...] = ()


class EvidenceSession:
    """Cache evidence lookups for one :func:`spokenform.prepare` call."""

    def __init__(self, provider: LexicalEvidenceProvider | None = None) -> None:
        self.provider = provider
        self._word_cache: dict[str, WordEvidence] = {}
        self._segment_cache: dict[tuple[str, int], tuple[LexicalSegmentEvidence, ...]] = {}
        self._domain_cache: dict[
            tuple[str, tuple[int, int], str, int, float, float], DomainEvidence | None
        ] = {}

    @property
    def available(self) -> bool:
        """Whether an evidence provider was supplied."""
        return self.provider is not None

    def word(self, value: str) -> WordEvidence | None:
        """Return cached word evidence, or ``None`` without a provider."""
        if self.provider is None:
            return None
        if value not in self._word_cache:
            self._word_cache[value] = self.provider.word(value)
        return self._word_cache[value]

    def segment(
        self, value: str, *, max_word_length: int = 32
    ) -> tuple[LexicalSegmentEvidence, ...]:
        """Return cached lexical segmentation evidence."""
        if self.provider is None:
            return ()
        key = (value, max_word_length)
        if key not in self._segment_cache:
            self._segment_cache[key] = self.provider.segment(value, max_word_length=max_word_length)
        return self._segment_cache[key]

    def supports(
        self,
        text: str,
        *,
        target: tuple[int, int],
        domain: str,
        window: int = 6,
        decay: float = 0.7,
        threshold: float = 0.4,
    ) -> DomainEvidence | None:
        """Return positive semantic evidence when semantic capability exists.

        Missing semantic capability is represented as unavailable evidence, not a
        negative result. This lets callers retain their existing fast paths.
        """
        if self.provider is None or "semantic" not in self.provider.capabilities:
            return None
        key = (text, target, domain, window, decay, threshold)
        if key not in self._domain_cache:
            self._domain_cache[key] = self.provider.supports_domain(
                text,
                target=target,
                domain=domain,
                window=window,
                decay=decay,
                threshold=threshold,
            )
        return self._domain_cache[key]

    @staticmethod
    def details(domain: str, evidence: DomainEvidence | None) -> EvidenceDetails | None:
        """Convert provider evidence into deterministic trace metadata."""
        if evidence is None:
            return None
        cues = tuple(cue.text for cue in evidence.cues)
        return EvidenceDetails(f"lexhint:{domain}", evidence.score, cues)


def validate_provider_language(provider: LexicalEvidenceProvider, language: str) -> None:
    """Reject providers whose language differs from Spokenform's base language."""
    spoken_language = base_language(normalize_language(language))
    provider_language = base_language(normalize_language(provider.language))
    if spoken_language != provider_language:
        raise ValueError(
            "lexical_evidence language mismatch: "
            f"Spokenform uses {spoken_language!r}, provider uses {provider_language!r}"
        )


def validate_provider(provider: LexicalEvidenceProvider | None, language: str) -> None:
    """Validate an explicitly supplied provider before normalization starts."""
    if provider is None:
        return
    validate_provider_language(provider, language)
    if "lexical" not in provider.capabilities:
        raise ValueError("lexical_evidence provider must declare the 'lexical' capability")


__all__ = [
    "ContextCueEvidence",
    "DomainEvidence",
    "EvidenceDetails",
    "EvidenceSession",
    "LexicalEvidenceProvider",
    "LexicalSegmentEvidence",
    "WordEvidence",
    "validate_provider",
    "validate_provider_language",
]
