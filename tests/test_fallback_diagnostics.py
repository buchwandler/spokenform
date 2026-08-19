from spokenform.config import SequenceFallbackMode
from spokenform.diagnostics import trace_sequence_fallback


def test_sequence_fallback_trace_distinguishes_preserve_and_spell() -> None:
    preserved = trace_sequence_fallback("AAPL", language="en", mode=SequenceFallbackMode.PRESERVE)
    spelled = trace_sequence_fallback("AAPL", language="en", mode="spell")

    assert preserved[0].status == "preserved"
    assert preserved[0].semantic_status == "unclaimed"
    assert preserved[0].rendered_text is None
    assert spelled[0].status == "spelled"
    assert spelled[0].action is SequenceFallbackMode.SPELL
    assert spelled[0].rendered_text == "A A P L"


def test_sequence_fallback_trace_marks_policy_suppression() -> None:
    records = trace_sequence_fallback(
        "H2O", language="en", mode="spell", suppressed_ranges=((0, 3),)
    )
    assert records[0].semantic_status == "suppressed"
    assert records[0].rule == "fallback.sequence"
