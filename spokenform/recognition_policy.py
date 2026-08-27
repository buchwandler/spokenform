"""Central policy decisions for structured recognition candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .config import InterpretationMode, RecognitionDomain, RecognitionEvidence
from .mapping import Replacement


@dataclass(frozen=True, slots=True)
class CandidatePolicyDecision:
    """The policy outcome for one generated structured candidate."""

    enabled: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PolicySuppression:
    """A generated candidate excluded by interpretation or domain policy."""

    start: int
    end: int
    rule: str | None
    domain: str | None
    evidence: str | None
    reason: str


_DOMAIN_BY_RULE: dict[str, RecognitionDomain] = {
    "sequence.address": RecognitionDomain.ADDRESSES,
    "sequence.biomedical": RecognitionDomain.BIOLOGY,
    "sequence.biology": RecognitionDomain.BIOLOGY,
    "sequence.formula": RecognitionDomain.CHEMISTRY,
    "sequence.math": RecognitionDomain.MATH,
    "sequence.music": RecognitionDomain.MUSIC,
    "sequence.sports": RecognitionDomain.SPORTS,
    "sequence.chained-score": RecognitionDomain.SPORTS,
    "sequence.countdown": RecognitionDomain.TEMPORAL,
    "sequence.ticker": RecognitionDomain.FINANCE,
    "sequence.parenthesized-ticker": RecognitionDomain.FINANCE,
    "sequence.exchange-rate": RecognitionDomain.FINANCE,
    "sequence.currency": RecognitionDomain.FINANCE,
    "sequence.currency-magnitude": RecognitionDomain.FINANCE,
    "sequence.social-hashtag": RecognitionDomain.SOCIAL,
    "sequence.social-mention": RecognitionDomain.SOCIAL,
    "sequence.coordinate": RecognitionDomain.GEOGRAPHY,
    "sequence.reference": RecognitionDomain.REFERENCES,
    "sequence.legal": RecognitionDomain.LEGAL,
    "sequence.url": RecognitionDomain.COMMUNICATIONS,
    "sequence.email": RecognitionDomain.COMMUNICATIONS,
    "sequence.phone": RecognitionDomain.COMMUNICATIONS,
    "sequence.phone-ambiguous": RecognitionDomain.COMMUNICATIONS,
    "sequence.emergency": RecognitionDomain.COMMUNICATIONS,
    "sequence.ipv4": RecognitionDomain.NETWORK,
    "sequence.mac": RecognitionDomain.NETWORK,
    "sequence.isbn": RecognitionDomain.IDENTIFIERS,
    "sequence.iban": RecognitionDomain.IDENTIFIERS,
    "sequence.uuid": RecognitionDomain.IDENTIFIERS,
    "sequence.vin": RecognitionDomain.IDENTIFIERS,
    "sequence.product": RecognitionDomain.IDENTIFIERS,
    "sequence.plate": RecognitionDomain.IDENTIFIERS,
    "sequence.version": RecognitionDomain.IDENTIFIERS,
    "sequence.postal": RecognitionDomain.IDENTIFIERS,
    "sequence.year": RecognitionDomain.TEMPORAL,
    "sequence.year-range": RecognitionDomain.TEMPORAL,
    "sequence.decade": RecognitionDomain.TEMPORAL,
    "sequence.quarter": RecognitionDomain.TEMPORAL,
    "sequence.duration": RecognitionDomain.TEMPORAL,
    "sequence.height": RecognitionDomain.QUANTITIES,
    "sequence.percent": RecognitionDomain.QUANTITIES,
    "sequence.compound-unit": RecognitionDomain.QUANTITIES,
    "sequence.fraction": RecognitionDomain.QUANTITIES,
    "sequence.numeric-range": RecognitionDomain.QUANTITIES,
    "sequence.temperature": RecognitionDomain.QUANTITIES,
    "sequence.acronym": RecognitionDomain.CORE,
    "sequence.parenthesized-initialism": RecognitionDomain.CORE,
    "sequence.roman": RecognitionDomain.REFERENCES,
    "sequence.symbol": RecognitionDomain.CORE,
}

_CONTEXTUAL_RULES = frozenset(
    {
        "sequence.address",
        "sequence.acronym",
        "sequence.biomedical",
        "sequence.biology",
        "sequence.countdown",
        "sequence.chained-score",
        "sequence.emergency",
        "sequence.parenthesized-initialism",
        "sequence.parenthesized-ticker",
        "sequence.phone-ambiguous",
        "sequence.product",
        "sequence.roman",
        "sequence.sports",
        "sequence.ticker",
        "sequence.version",
        "sequence.year",
        "sequence.year-range",
        "sequence.reference",
        "sequence.legal",
    }
)

_LOCALE_DOMAIN_BY_PREFIX: dict[str, RecognitionDomain] = {
    "date": RecognitionDomain.TEMPORAL,
    "time": RecognitionDomain.TEMPORAL,
    "decade": RecognitionDomain.TEMPORAL,
    "currency": RecognitionDomain.FINANCE,
    "magnitude-currency": RecognitionDomain.FINANCE,
    "quantity": RecognitionDomain.QUANTITIES,
    "temperature": RecognitionDomain.QUANTITIES,
    "ordinal": RecognitionDomain.QUANTITIES,
    "number": RecognitionDomain.QUANTITIES,
    "version_decimal": RecognitionDomain.IDENTIFIERS,
    "short-year": RecognitionDomain.TEMPORAL,
    "text-date": RecognitionDomain.TEMPORAL,
    "mixed-text-date": RecognitionDomain.TEMPORAL,
    "date-range": RecognitionDomain.TEMPORAL,
    "time-range": RecognitionDomain.TEMPORAL,
    "label": RecognitionDomain.IDENTIFIERS,
    "plural_tens": RecognitionDomain.QUANTITIES,
}


def normalize_domain(value: RecognitionDomain | str | None) -> RecognitionDomain | None:
    """Normalize candidate or configuration domain values."""
    if value is None:
        return None
    if isinstance(value, RecognitionDomain):
        return value
    try:
        return RecognitionDomain(value)
    except (TypeError, ValueError):
        return None


def normalize_evidence(value: RecognitionEvidence | str | None) -> RecognitionEvidence | None:
    """Normalize candidate evidence values."""
    if value is None:
        return None
    if isinstance(value, RecognitionEvidence):
        return value
    try:
        return RecognitionEvidence(value)
    except (TypeError, ValueError):
        return None


def domain_for_rule(rule: str | None) -> RecognitionDomain | None:
    """Return the canonical domain for a rule identifier."""
    if not rule:
        return None
    if rule in _DOMAIN_BY_RULE:
        return _DOMAIN_BY_RULE[rule]
    if "." in rule:
        prefix, name = rule.split(".", 1)
        if prefix in {"en", "de", "es", "fr", "it", "pt", "cs", "sv", "vi"}:
            return _LOCALE_DOMAIN_BY_PREFIX.get(name.split(".", 1)[0])
    return None


def evidence_for_rule(rule: str | None) -> RecognitionEvidence | None:
    """Return explicit evidence metadata for a known rule."""
    if not rule:
        return None
    if rule in _CONTEXTUAL_RULES:
        return RecognitionEvidence.CONTEXTUAL
    if domain_for_rule(rule) is not None:
        return RecognitionEvidence.INTRINSIC
    if "." in rule and rule.split(".", 1)[0] in {"en", "de", "es", "fr", "it", "pt", "cs", "sv"}:
        return RecognitionEvidence.INTRINSIC
    return None


def annotate_candidate(candidate: Replacement) -> Replacement:
    """Attach canonical policy metadata without changing source coordinates."""
    domain = normalize_domain(candidate.recognition_domain) or domain_for_rule(candidate.rule)
    evidence = normalize_evidence(candidate.recognition_evidence) or evidence_for_rule(
        candidate.rule
    )
    if domain is None and evidence is None:
        return candidate
    return replace(
        candidate,
        recognition_domain=domain.value if domain is not None else None,
        recognition_evidence=evidence.value if evidence is not None else None,
    )


def decide_candidate(
    candidate: Replacement,
    *,
    interpretation_mode: InterpretationMode,
    disabled_domains: frozenset[RecognitionDomain],
    allowed_domains: frozenset[RecognitionDomain] | None = None,
) -> CandidatePolicyDecision:
    """Decide whether a candidate may enter precedence resolution.

    Contextual mode preserves legacy behavior for candidates that have not yet
    been annotated. Surface mode is intentionally fail-closed: only an
    explicitly intrinsic candidate is eligible.
    """
    if not isinstance(interpretation_mode, InterpretationMode):
        interpretation_mode = InterpretationMode(interpretation_mode)
    domain = normalize_domain(candidate.recognition_domain)
    if domain is not None and domain in disabled_domains:
        return CandidatePolicyDecision(False, "disabled-domain")
    if allowed_domains is not None:
        if domain is None or domain not in allowed_domains:
            return CandidatePolicyDecision(False, "domain-not-allowed")
    if interpretation_mode is InterpretationMode.SURFACE:
        evidence = normalize_evidence(candidate.recognition_evidence)
        if evidence is not RecognitionEvidence.INTRINSIC:
            return CandidatePolicyDecision(False, "context-not-allowed")
    return CandidatePolicyDecision(True)


def candidate_is_enabled(
    candidate: Replacement,
    *,
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: frozenset[RecognitionDomain] = frozenset(),
    allowed_domains: frozenset[RecognitionDomain] | None = None,
) -> bool:
    """Return whether a candidate is eligible under the recognition policy."""
    return decide_candidate(
        candidate,
        interpretation_mode=interpretation_mode,
        disabled_domains=disabled_domains,
        allowed_domains=allowed_domains,
    ).enabled


def filter_candidates(
    candidates: tuple[Replacement, ...],
    *,
    interpretation_mode: InterpretationMode,
    disabled_domains: frozenset[RecognitionDomain],
    allowed_domains: frozenset[RecognitionDomain] | None,
) -> tuple[tuple[Replacement, ...], tuple[PolicySuppression, ...]]:
    """Filter candidates before precedence and reserve disabled-domain spans."""
    if not isinstance(interpretation_mode, InterpretationMode):
        interpretation_mode = InterpretationMode(interpretation_mode)
    disabled_domains = frozenset(
        domain if isinstance(domain, RecognitionDomain) else RecognitionDomain(domain)
        for domain in disabled_domains
    )
    if allowed_domains is not None:
        allowed_domains = frozenset(
            domain if isinstance(domain, RecognitionDomain) else RecognitionDomain(domain)
            for domain in allowed_domains
        )
    annotated = tuple(annotate_candidate(candidate) for candidate in candidates)
    eligible: list[Replacement] = []
    suppressed: list[PolicySuppression] = []
    blocked_ranges: list[tuple[int, int]] = []
    for candidate in annotated:
        decision = decide_candidate(
            candidate,
            interpretation_mode=interpretation_mode,
            disabled_domains=disabled_domains,
            allowed_domains=allowed_domains,
        )
        if decision.enabled:
            eligible.append(candidate)
            continue
        suppressed.append(
            PolicySuppression(
                candidate.start,
                candidate.end,
                candidate.rule,
                candidate.recognition_domain,
                candidate.recognition_evidence,
                decision.reason or "policy-suppressed",
            )
        )
        if decision.reason in {"disabled-domain", "domain-not-allowed"}:
            blocked_ranges.append((candidate.start, candidate.end))
    if blocked_ranges:
        kept: list[Replacement] = []
        for candidate in eligible:
            if any(
                candidate.start < end and start < candidate.end for start, end in blocked_ranges
            ):
                suppressed.append(
                    PolicySuppression(
                        candidate.start,
                        candidate.end,
                        candidate.rule,
                        candidate.recognition_domain,
                        candidate.recognition_evidence,
                        "blocked-by-disabled-domain",
                    )
                )
            else:
                kept.append(candidate)
        eligible = kept
    return tuple(eligible), tuple(suppressed)


__all__ = [
    "CandidatePolicyDecision",
    "PolicySuppression",
    "annotate_candidate",
    "filter_candidates",
    "candidate_is_enabled",
    "decide_candidate",
    "domain_for_rule",
    "evidence_for_rule",
    "normalize_domain",
    "normalize_evidence",
]
