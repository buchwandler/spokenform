"""Render a self-contained Spokenform Gold benchmark report."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .html_report import (
    KPI,
    FilterControl,
    Section,
    data_attributes,
    details_block,
    escape,
    json_pre,
    number,
    percent,
    render_filter_controls,
    render_page,
)


def _gold_summary(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("summary", {})
    return value if isinstance(value, dict) else {}


def _kpis(summary: dict[str, Any]) -> tuple[KPI, ...]:
    gold = _gold_summary(summary)
    mode = summary.get("mode", "canonical")
    primary_label = f"Primary accuracy ({mode})"
    excluded = int(gold.get("excluded_count", 0) or 0)
    ambiguous = int(gold.get("ambiguous_count", 0) or 0)
    quarantine = int(gold.get("quarantine_count", 0) or 0)
    return (
        KPI("Scorable records", number(gold.get("records_scorable", 0))),
        KPI(primary_label, percent(gold.get("primary_accuracy", 0)), mode),
        KPI("Canonical accuracy", percent(gold.get("sentence_canonical_accuracy", 0))),
        KPI("Accepted accuracy", percent(gold.get("accepted_variant_accuracy", 0))),
        KPI("No-change accuracy", percent(gold.get("no_change_accuracy", 0))),
        KPI("False-positive rate", percent(gold.get("false_positive_normalization_rate", 0))),
        KPI("Excluded", number(excluded), f"{ambiguous} ambiguous · {quarantine} quarantine"),
    )


def _aggregate_table(mapping: dict[str, Any], label: str) -> str:
    rows = []
    for key, values in sorted(mapping.items()):
        values = values if isinstance(values, dict) else {}
        records = int(values.get("records", 0) or 0)
        canonical = int(values.get("canonical_matches", 0) or 0)
        accepted = int(values.get("accepted_matches", 0) or 0)
        rows.append(
            "<tr>"
            f"<th>{escape(key)}</th>"
            f"<td>{number(records)}</td>"
            f"<td>{number(canonical)}</td><td>{percent(canonical / records if records else 0)}</td>"
            f"<td>{number(accepted)}</td><td>{percent(accepted / records if records else 0)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(f'<tr><td colspan="6">No {escape(label.lower())} data.</td></tr>')
    return (
        '<div class="table-scroll"><table><thead><tr>'
        f"<th>{escape(label)}</th><th>Records</th><th>Canonical matches</th>"
        "<th>Canonical accuracy</th><th>Accepted matches</th><th>Accepted accuracy</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _overview(summary: dict[str, Any]) -> str:
    gold = _gold_summary(summary)
    lines = [
        f"<p><strong>Selection:</strong> {escape(summary.get('selection', summary.get('split') or 'corpus'))}</p>",
        f"<p><strong>Scoring mode:</strong> {escape(summary.get('mode', 'canonical'))}</p>",
        f"<p><strong>Profile:</strong> {escape(summary.get('profile_name', 'unknown'))}</p>",
        f"<p><strong>Total records:</strong> {number(gold.get('records_total', summary.get('record_count', 0)))}; "
        f"<strong>Scorable:</strong> {number(gold.get('records_scorable', 0))}</p>",
        f"<p><strong>Ambiguous:</strong> {number(gold.get('ambiguous_count', 0))}; "
        f"<strong>Quarantine:</strong> {number(gold.get('quarantine_count', 0))}</p>",
        "<p>Canonical mode requires the Gold canonical output. Accepted mode permits Gold-declared accepted variants. "
        "Ambiguous and quarantine records are excluded from scoring. No-change records measure false-positive normalization.</p>",
    ]
    return "".join(lines)


def _status_table(summary: dict[str, Any]) -> str:
    gold = _gold_summary(summary)
    body = _aggregate_table(gold.get("per_status", {}), "Status")
    excluded = (
        '<h3>Excluded statuses</h3><div class="table-scroll"><table><thead><tr>'
        "<th>Status</th><th>Records</th></tr></thead><tbody>"
        f"<tr><td>ambiguous</td><td>{number(gold.get('ambiguous_count', 0))}</td></tr>"
        f"<tr><td>quarantine</td><td>{number(gold.get('quarantine_count', 0))}</td></tr>"
        "</tbody></table></div>"
    )
    return body + excluded


def _failure_details(row: dict[str, Any]) -> str:
    return details_block(
        "Record metadata",
        json_pre(
            {
                "family_id": row.get("family_id"),
                "accepted_variants": row.get("accepted_variants", []),
                "negative_for": row.get("negative_for", []),
                "source_benchmarks": row.get("source_benchmarks", []),
                "source_observations": row.get("source_observations", []),
                "units": row.get("units", []),
            }
        ),
    )


def _failure_table(rows: tuple[dict[str, Any], ...]) -> str:
    controls = render_filter_controls(
        "spokenform-gold-failures",
        (
            FilterControl(
                "text", "Search", mode="row-text", placeholder="ID, original, expected, actual"
            ),
            FilterControl(
                "language",
                "Language",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("language", "")) for row in rows if row.get("language")}
                    )
                ),
            ),
            FilterControl(
                "locale",
                "Locale",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("locale", "")) for row in rows if row.get("locale")}
                    )
                ),
            ),
            FilterControl(
                "status",
                "Status",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("status", "")) for row in rows if row.get("status")}
                    )
                ),
            ),
            FilterControl("category", "Category", placeholder="time"),
            FilterControl("source-benchmark", "Source", placeholder="spokenform_curated"),
        ),
    )
    rendered = []
    for row in rows:
        rendered.append(
            f'<tr data-filter-row="spokenform-gold-failures" '
            f"{data_attributes({'language': row.get('language', ''), 'locale': row.get('locale', ''), 'status': row.get('status', ''), 'category': ','.join(row.get('categories', [])), 'source-benchmark': row.get('source_benchmark', '')})}>"
            f"<td>{escape(row.get('id', ''))}</td>"
            f"<td>{escape(row.get('language', ''))}</td>"
            f"<td>{escape(row.get('locale', ''))}</td>"
            f"<td>{escape(row.get('status', ''))}</td>"
            f"<td>{escape(', '.join(row.get('categories', [])))}</td>"
            f"<td>{escape(row.get('family_id', ''))}</td>"
            f"<td>{escape(row.get('input', ''))}</td>"
            f"<td>{escape(row.get('expected', ''))}</td>"
            f"<td>{escape('; '.join(row.get('accepted_variants', [])))}</td>"
            f"<td>{escape(row.get('actual', ''))}</td>"
            f"<td>{escape(row.get('source_benchmark', ''))}</td>"
            f"<td>{_failure_details(row)}</td>"
            "</tr>"
        )
    if not rendered:
        rendered.append('<tr><td colspan="12">No primary failures.</td></tr>')
    return (
        f"<p>{number(len(rows))} primary failure rows are available before local filters.</p>"
        f"{controls}"
        '<p class="muted" data-empty-for="spokenform-gold-failures" hidden>No failure rows match the current filters.</p>'
        '<div class="table-scroll"><table><thead><tr>'
        "<th>ID</th><th>Language</th><th>Locale</th><th>Status</th><th>Category</th>"
        "<th>Family</th><th>Original</th><th>Expected canonical</th><th>Accepted variants</th>"
        "<th>Actual</th><th>Source</th><th>Metadata</th>"
        f"</tr></thead><tbody>{''.join(rendered)}</tbody></table></div>"
    )


def _metadata(summary: dict[str, Any]) -> str:
    metadata = {
        "run_id": summary.get("run_id"),
        "timestamp": summary.get("timestamp_utc"),
        "spokenform_version": summary.get("spokenform_version"),
        "spokenform_commit": summary.get("spokenform_commit"),
        "gold_repository": summary.get("adapter", {}).get("repository"),
        "gold_source_commit": summary.get("adapter", {}).get("dataset_commit"),
        "gold_benchmark_version": summary.get("spokenform_gold_version"),
        "gold_manifest_hash": summary.get("gold_manifest_hash"),
        "profile": summary.get("profile_name"),
        "profile_config": summary.get("profile_config"),
        "mode": summary.get("mode"),
        "split": summary.get("split"),
        "source_mode": summary.get("adapter", {}).get("source_mode"),
        "configuration_hash": summary.get("identity", {}).get("configuration_hash"),
    }
    return json_pre(metadata) + details_block("Full summary snapshot", json_pre(summary))


def render_report(
    summary: dict[str, Any], rows: Iterable[dict[str, Any]], output: Path | str
) -> Path:
    """Write a self-contained report without changing benchmark results."""
    rows_tuple = tuple(rows)
    failures = tuple(row for row in rows_tuple if not row.get("primary_match"))
    gold = _gold_summary(summary)
    sections = [
        Section("overview", "Overview", "Overview", _overview(summary), active=True),
        Section(
            "categories",
            "Categories",
            "Category metrics",
            _aggregate_table(gold.get("per_category", {}), "Category"),
        ),
        Section(
            "languages",
            "Languages",
            "Language and locale metrics",
            "<h3>Languages</h3>"
            + _aggregate_table(gold.get("per_language", {}), "Language")
            + "<h3>Locales</h3>"
            + _aggregate_table(gold.get("per_locale", {}), "Locale"),
        ),
        Section("statuses", "Statuses", "Status metrics", _status_table(summary)),
        Section("failures", "Failures", "Failure explorer", _failure_table(failures)),
        Section("metadata", "Metadata", "Run provenance", _metadata(summary)),
    ]
    source = summary.get("adapter", {}).get("dataset_commit") or "explicit local release"
    subtitle = f"{source} | {number(summary.get('record_count', 0))} selected records | {summary.get('mode', 'canonical')} mode"
    return render_page(
        title="Spokenform Gold benchmark",
        subtitle=subtitle,
        sections=sections,
        output=output,
        kpis=_kpis(summary),
        intro_html="<p>This self-contained report mirrors the Gold scoring artifacts and adapter provenance.</p>",
    )


__all__ = ["render_report"]
