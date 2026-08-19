"""Render a self-contained static PolyNorm benchmark report."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .html_report import (
    KPI,
    FilterControl,
    Section,
    data_attributes,
    decimal,
    details_block,
    escape,
    json_pre,
    number,
    percent,
    render_filter_controls,
    render_page,
)


def _kpis(summary: dict[str, Any]) -> tuple[KPI, ...]:
    return (
        KPI("Cases", number(summary.get("cases", 0))),
        KPI(
            "Speech exact",
            percent(summary.get("speech_exact_rate", 0)),
            f"{number(summary.get('speech_exact_count', 0))} / {number(summary.get('cases', 0))}",
        ),
        KPI(
            "Speech equivalent",
            percent(summary.get("speech_exact_equivalent_rate", 0)),
            f"{number(summary.get('speech_exact_equivalent_count', 0))} / {number(summary.get('cases', 0))}",
        ),
        KPI("Semantic failures", number(summary.get("semantic_failure_count", 0))),
        KPI("Presentation-only", number(summary.get("presentation_only_count", 0))),
        KPI("Mean speech WER", decimal(summary.get("mean_speech_wer", 0))),
        KPI("Quarantined rows", number(summary.get("quarantine_count", 0))),
    )


def _rate_cell(values: dict[str, Any], count_key: str, rate_key: str) -> str:
    return (
        f"<strong>{percent(values.get(rate_key, 0))}</strong>"
        f"<small>{number(values.get(count_key, 0))} / {number(values.get('cases', 0))}</small>"
    )


def _count_cell(values: dict[str, Any], key: str) -> str:
    count = int(values.get(key, 0) or 0)
    total = int(values.get("cases", 0) or 0)
    ratio = percent(count / total if total else 0)
    return f"<strong>{number(count)}</strong><small>{ratio} of {number(total)}</small>"


def _metrics_table(mapping: dict[str, dict[str, Any]], *, label: str) -> str:
    rows = []
    for key, values in sorted(mapping.items()):
        rows.append(
            "<tr>"
            f"<th>{escape(key)}</th>"
            f"<td>{number(values.get('cases', 0))}</td>"
            f"<td>{_rate_cell(values, 'literal_exact_count', 'literal_exact_rate')}</td>"
            f"<td>{_rate_cell(values, 'speech_exact_count', 'speech_exact_rate')}</td>"
            f"<td>{_rate_cell(values, 'speech_exact_equivalent_count', 'speech_exact_equivalent_rate')}</td>"
            f"<td>{_count_cell(values, 'presentation_only_count')}</td>"
            f"<td>{_count_cell(values, 'semantic_failure_count')}</td>"
            f"<td>{decimal(values.get('mean_speech_wer', 0))}</td>"
            f"<td>{number(values.get('error_count', 0))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-scroll"><table><thead><tr>'
        f"<th>{escape(label)}</th><th>Cases</th><th>Literal exact</th><th>Speech exact</th>"
        "<th>Speech equivalent</th><th>Presentation-only</th><th>Semantic failures</th>"
        "<th>Mean speech WER</th><th>Errors</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _locale_category_table(summary: dict[str, Any]) -> str:
    rows = []
    for locale, categories in sorted(summary.get("by_locale_category", {}).items()):
        for category, values in sorted(categories.items()):
            rows.append(
                "<tr>"
                f"<td>{escape(locale)}</td><td>{escape(category)}</td>"
                f"<td>{number(values.get('cases', 0))}</td>"
                f"<td>{_rate_cell(values, 'speech_exact_equivalent_count', 'speech_exact_equivalent_rate')}</td>"
                f"<td>{_count_cell(values, 'semantic_failure_count')}</td>"
                f"<td>{decimal(values.get('mean_speech_wer', 0))}</td>"
                "</tr>"
            )
    return (
        '<div class="table-scroll"><table><thead><tr>'
        "<th>Locale</th><th>Canonical category</th><th>Cases</th><th>Speech equivalent</th>"
        "<th>Semantic failures</th><th>Mean speech WER</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _key_value_table(mapping: dict[str, Any], *, key_label: str, value_label: str = "Value") -> str:
    rows = "".join(
        f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>"
        for key, value in sorted(mapping.items())
    )
    if not rows:
        rows = '<tr><td colspan="2">No values.</td></tr>'
    return (
        '<div class="table-scroll"><table><thead><tr>'
        f"<th>{escape(key_label)}</th><th>{escape(value_label)}</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _diagnostics_section(summary: dict[str, Any]) -> str:
    numeric_gate = summary.get("numeric_gate", {})
    return (
        '<div class="two-column">'
        '<div class="subsection"><h3>Gate metrics</h3>'
        f"{json_pre(summary.get('gate_metrics', {}))}</div>"
        '<div class="subsection"><h3>Diagnostic aggregates</h3>'
        f"{json_pre(summary.get('diagnostic_aggregates', {}))}</div>"
        '<div class="subsection"><h3>Outcome counts</h3>'
        f"{_key_value_table(summary.get('outcome_counts', {}), key_label='Outcome', value_label='Count')}</div>"
        '<div class="subsection"><h3>Risk tiers</h3>'
        f"{_key_value_table(summary.get('risk_tier_counts', {}), key_label='Risk tier', value_label='Count')}</div>"
        '<div class="subsection"><h3>Quarantine reason codes</h3>'
        f"{_key_value_table(summary.get('quarantine_reason_codes', {}), key_label='Reason code', value_label='Count')}</div>"
        '<div class="subsection"><h3>Numeric gate</h3>'
        f"{json_pre(numeric_gate if isinstance(numeric_gate, dict) else {})}</div>"
        "</div>"
    )


def _failure_rows(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        row
        for row in rows
        if row.get("error") or not row.get("literal_exact") or not row.get("speech_exact")
    )


def _failure_details(row: dict[str, Any]) -> str:
    payload = {
        "id": row.get("id"),
        "primary_rule": row.get("primary_rule"),
        "failure_phase": row.get("failure_phase"),
        "render_mode": row.get("render_mode"),
        "winning_span": row.get("winning_span"),
        "structured_claimed": row.get("structured_claimed"),
        "claim_owner": row.get("claim_owner"),
        "protected_reason": row.get("protected_reason"),
        "quarantine": row.get("quarantine"),
        "source_rules": row.get("source_rules"),
        "changed_stages": row.get("changed_stages"),
        "error": row.get("error"),
    }
    return details_block("Details", json_pre(payload))


def _failure_table(rows: tuple[dict[str, Any], ...]) -> str:
    filters = render_filter_controls(
        "polynorm-failures",
        [
            FilterControl("text", "Search", mode="row-text", placeholder="Search rows"),
            FilterControl(
                "locale",
                "Locale",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {
                            str(row.get("polynorm_locale", ""))
                            for row in rows
                            if row.get("polynorm_locale")
                        }
                    )
                ),
            ),
            FilterControl("category", "Category", placeholder="Cardinal"),
            FilterControl(
                "outcome",
                "Outcome",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("outcome", "")) for row in rows if row.get("outcome")}
                    )
                ),
            ),
            FilterControl(
                "failure-family",
                "Family",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {
                            str(row.get("failure_family", ""))
                            for row in rows
                            if row.get("failure_family")
                        }
                    )
                ),
            ),
            FilterControl(
                "ownership",
                "Ownership",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("ownership", "")) for row in rows if row.get("ownership")}
                    )
                ),
            ),
            FilterControl(
                "risk",
                "Risk",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("risk_tier", "")) for row in rows if row.get("risk_tier")}
                    )
                ),
            ),
            FilterControl(
                "speech-wer",
                "Min WER",
                control="number",
                mode="min-number",
                placeholder="0.25",
                step="0.01",
            ),
        ],
    )
    rendered_rows = []
    for row in rows:
        attrs = data_attributes(
            {
                "locale": row.get("polynorm_locale", ""),
                "category": row.get("canonical_category", ""),
                "outcome": row.get("outcome", ""),
                "failure-family": row.get("failure_family", ""),
                "ownership": row.get("ownership", ""),
                "risk": row.get("risk_tier", ""),
                "speech-wer": row.get("speech_wer", 0),
            }
        )
        rendered_rows.append(
            f'<tr data-filter-row="polynorm-failures" {attrs}>'
            f"<td>{escape(row.get('id', ''))}</td>"
            f"<td>{escape(row.get('polynorm_locale', ''))}</td>"
            f"<td>{escape(row.get('category', ''))}</td>"
            f"<td>{escape(row.get('canonical_category', ''))}</td>"
            f"<td>{escape(row.get('original_text', ''))}</td>"
            f"<td>{escape(row.get('expected', ''))}</td>"
            f"<td>{escape(row.get('actual', ''))}</td>"
            f"<td>{escape(row.get('outcome', ''))}</td>"
            f"<td>{decimal(row.get('speech_wer', 0))}</td>"
            f"<td>{escape(row.get('failure_family', ''))}</td>"
            f"<td>{escape(row.get('ownership', ''))}</td>"
            f"<td>{escape(row.get('risk_tier', ''))}</td>"
            f"<td>{_failure_details(row)}</td>"
            "</tr>"
        )
    if not rendered_rows:
        rendered_rows.append(
            '<tr data-empty-for="polynorm-failures"><td colspan="13">No failures.</td></tr>'
        )
    return (
        f"<p>{number(len(rows))} failure rows are available before local filters are applied.</p>"
        f"{filters}"
        '<p class="muted" data-empty-for="polynorm-failures" hidden>No failure rows match the current filters.</p>'
        '<div class="table-scroll"><table><thead><tr>'
        "<th>Case</th><th>Locale</th><th>Category</th><th>Canonical category</th><th>Source</th>"
        "<th>Expected</th><th>Actual</th><th>Outcome</th><th>Speech WER</th><th>Family</th>"
        "<th>Ownership</th><th>Risk</th><th>Diagnostics</th>"
        f"</tr></thead><tbody>{''.join(rendered_rows)}</tbody></table></div>"
    )


def _oracle_section(summary: dict[str, Any]) -> str:
    oracle = summary.get("candidate_oracle")
    if not isinstance(oracle, dict):
        return ""
    headline = {
        key: oracle.get(key)
        for key in (
            "schema_version",
            "enabled",
            "cases",
            "eligible_cases",
            "eligible_semantic_failure_count",
            "scorable_cases",
            "selection_gap_count",
            "selection_gap_rate",
            "fully_recoverable_selection_gap_count",
            "fully_recoverable_selection_gap_rate",
            "selector_regret_mean",
            "candidate_recall_for_exact_target",
        )
    }
    return (
        "<h3>Candidate selection oracle</h3>"
        "<p>Selection gap rate is selection gaps divided by eligible semantic failures. "
        "Fully recoverable selection gap rate uses the same denominator and counts only "
        "selection alternatives that reach speech equivalence.</p>"
        f"{json_pre(headline)}" + details_block("Full oracle summary", json_pre(oracle))
    )


def render_report(
    summary: dict[str, Any], rows: Iterable[dict[str, Any]], output: Path | str
) -> Path:
    """Write one self-contained HTML report and return its path."""
    rows_tuple = tuple(rows)
    metadata = {
        "benchmark": summary.get("benchmark"),
        "generated_at": summary.get("generated_at"),
        "dataset_commit": summary.get("dataset_commit"),
        "repository": summary.get("repository"),
        "profile": summary.get("profile"),
        "locales": summary.get("locales"),
        "spokenform_languages": summary.get("spokenform_languages"),
        "environment": summary.get("environment"),
        "identity": summary.get("identity"),
    }
    sections = [
        Section(
            "overview",
            "Overview",
            "Overview",
            _metrics_table(summary.get("by_locale", {}), label="Locale"),
            active=True,
        ),
        Section(
            "categories",
            "Canonical categories",
            "Canonical-category table",
            _metrics_table(summary.get("by_canonical_category", {}), label="Canonical category"),
        ),
        Section(
            "locale-category",
            "Locale × category",
            "Locale × category view",
            _locale_category_table(summary),
        ),
        Section(
            "diagnostics", "Diagnostics", "Diagnostics and gate view", _diagnostics_section(summary)
        ),
        Section(
            "failures", "Failures", "Failure explorer", _failure_table(_failure_rows(rows_tuple))
        ),
        Section(
            "metadata",
            "Metadata",
            "Run metadata",
            f"{json_pre(metadata)}" + details_block("Full summary snapshot", json_pre(summary)),
        ),
    ]
    if isinstance(summary.get("candidate_oracle"), dict):
        sections.append(
            Section("oracle", "Oracle", "Optional oracle view", _oracle_section(summary))
        )
    subtitle = (
        f"profile {summary.get('profile', 'default')} | "
        f"dataset {summary.get('dataset_commit', 'unknown')} | "
        f"{number(summary.get('cases', 0))} cases"
    )
    return render_page(
        title="PolyNorm diagnostic benchmark",
        subtitle=subtitle,
        sections=sections,
        output=output,
        kpis=_kpis(summary),
        intro_html=(
            "<p>This self-contained report mirrors the local JSONL and summary artifacts without changing benchmark scoring or ownership semantics.</p>"
        ),
    )


__all__ = ["render_report"]
