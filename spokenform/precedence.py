"""Named semantic precedence for structured candidate conflicts.

The numeric values are intentionally centralized here.  Recognizers may still
provide a small local specificity adjustment, but the ownership family is
defined once so regex iteration order cannot silently become policy.
"""

from __future__ import annotations

from enum import IntEnum


class SequencePriority(IntEnum):
    """Relative priority of structured semantic ownership families."""

    PROTECTED_LITERAL = 120
    LABELED_IDENTIFIER = 110
    EXPLICIT_DATE = 105
    EXPLICIT_TIME = 100
    DURATION = 115
    REFERENCE = 95
    COUNTDOWN = 92
    SCORE = 90
    VERSION = 85
    TYPED_CODE = 80
    QUANTITY = 70
    YEAR = 65
    NUMERIC_RANGE = 50
    PHONE_AMBIGUOUS = 35
    GENERIC_NUMBER = 20
    SYMBOL = 10


_RULE_PRIORITIES: dict[str, int] = {
    "sequence.url": SequencePriority.PROTECTED_LITERAL,
    "sequence.email": SequencePriority.PROTECTED_LITERAL,
    "sequence.isbn": SequencePriority.LABELED_IDENTIFIER,
    "sequence.vin": SequencePriority.LABELED_IDENTIFIER,
    "sequence.uuid": SequencePriority.LABELED_IDENTIFIER,
    "sequence.ipv4": SequencePriority.TYPED_CODE,
    "sequence.version": SequencePriority.VERSION,
    "sequence.reference": SequencePriority.REFERENCE,
    "sequence.legal": SequencePriority.LABELED_IDENTIFIER,
    "sequence.countdown": SequencePriority.COUNTDOWN,
    "sequence.sports": SequencePriority.SCORE,
    "sequence.chained-score": SequencePriority.SCORE,
    "sequence.time": SequencePriority.EXPLICIT_TIME,
    "sequence.quarter": SequencePriority.EXPLICIT_DATE,
    "sequence.duration": SequencePriority.DURATION,
    "es.time": SequencePriority.EXPLICIT_TIME,
    "sequence.quantity": SequencePriority.QUANTITY,
    "en.quantity": SequencePriority.QUANTITY,
    "sequence.year": SequencePriority.YEAR,
    "sequence.year-range": SequencePriority.YEAR,
    "sequence.numeric-range": SequencePriority.NUMERIC_RANGE,
    "sequence.phone-ambiguous": SequencePriority.PHONE_AMBIGUOUS,
    "sequence.phone": SequencePriority.TYPED_CODE,
    "sequence.mac": SequencePriority.TYPED_CODE,
    "sequence.biomedical": SequencePriority.LABELED_IDENTIFIER,
    "sequence.biology": SequencePriority.LABELED_IDENTIFIER,
    "sequence.height": SequencePriority.TYPED_CODE,
    "sequence.address": SequencePriority.TYPED_CODE,
    "sequence.coordinate": SequencePriority.TYPED_CODE,
    "sequence.compound-unit": SequencePriority.TYPED_CODE,
    "en.decade": 80,
    "sequence.decade": 78,
    "de.mixed-text-date": SequencePriority.EXPLICIT_DATE,
}


def priority_for_rule(rule: str | None) -> int:
    """Return the centralized priority for a rule, with a safe default."""
    if not rule:
        return int(SequencePriority.GENERIC_NUMBER)
    if rule in _RULE_PRIORITIES:
        return int(_RULE_PRIORITIES[rule])
    if rule.startswith("sequence.plate") or rule.startswith("sequence.product"):
        return int(SequencePriority.TYPED_CODE)
    if "date" in rule:
        return int(SequencePriority.EXPLICIT_DATE)
    if ".time" in rule:
        return int(SequencePriority.EXPLICIT_TIME)
    if ".quantity" in rule or ".currency" in rule:
        return int(SequencePriority.QUANTITY)
    if ".year" in rule:
        return int(SequencePriority.YEAR)
    return int(SequencePriority.GENERIC_NUMBER)


__all__ = ["SequencePriority", "priority_for_rule"]
