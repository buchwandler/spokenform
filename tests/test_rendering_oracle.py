from __future__ import annotations

from benchmarks.rendering_oracle import (
    analysis_fields,
    analyze_renderer_oracle,
    documented_render_alternatives,
    oracle_aggregates,
    time_render_alternatives,
)


def test_time_renderer_oracle_is_bounded_and_does_not_search_free_text() -> None:
    alternatives = documented_render_alternatives("14:00", family="time")
    assert [item.mode for item in alternatives] == [
        "digits",
        "oh-digits",
        "military/hundred",
        "military/hundred-hours",
    ]
    assert documented_render_alternatives("14:00", family="unknown") == ()
    assert len(time_render_alternatives(14, 0)) == 4


def test_renderer_oracle_reports_regret_from_allowed_alternatives() -> None:
    alternatives = documented_render_alternatives("14:00", family="time")
    analysis = analyze_renderer_oracle(
        "fourteen o'clock",
        "fourteen zero zero",
        language="en",
        family="time",
        baseline_mode="clock",
        alternatives=alternatives,
    )
    fields = analysis_fields(analysis)
    assert analysis.scorable
    assert analysis.best_mode == "digits"
    assert analysis.renderer_regret > 0.0
    assert fields["renderer_oracle_enabled"] is True


def test_renderer_aggregates_keep_unscorable_rows_visible() -> None:
    rows = [
        analysis_fields(
            analyze_renderer_oracle(
                "unchanged",
                "target",
                language="en",
                family="identifier",
                baseline_mode="digits",
                alternatives=(),
            )
        )
    ]
    summary = oracle_aggregates(rows)
    assert summary["cases"] == 1
    assert summary["scorable_cases"] == 0
