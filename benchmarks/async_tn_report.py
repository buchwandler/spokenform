"""Render a self-contained static Async TN benchmark report."""

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
    notice,
    number,
    percent,
    render_filter_controls,
    render_page,
)

DEFAULT_MIN_UNITS = 30


def _reference_models(reference: dict[str, Any], suite: str) -> tuple[dict[str, Any], ...]:
    categories = reference.get(suite, {}).get("categories", {})
    return tuple(categories.get("model_order", ()))


def _reference_category_map(reference: dict[str, Any], suite: str) -> dict[str, dict[str, Any]]:
    categories = reference.get(suite, {}).get("categories", {}).get("categories", ())
    return {
        str(row.get("category")): dict(row.get("models", {}))
        for row in categories
        if isinstance(row, dict) and row.get("category")
    }


def _kpis(summary: dict[str, Any]) -> tuple[KPI, ...]:
    counts = summary.get("counts", {})
    sentence = summary.get("sentence_metrics", {})
    unit = summary.get("unit_metrics", {})
    return (
        KPI(
            "Sentence speech-equivalent",
            percent(
                sentence.get("speech_equivalent", 0) / sentence.get("total", 1)
                if sentence.get("total")
                else 0
            ),
            f"{number(sentence.get('speech_equivalent', 0))} / {number(sentence.get('total', 0))}",
        ),
        KPI(
            "Unit speech-equivalent",
            percent(unit.get("accuracy", 0)),
            f"{number(counts.get('units_scorable', 0))} scorable units",
        ),
        KPI("Mean speech WER", decimal(unit.get("mean_speech_wer", 0))),
        KPI("Total units", number(counts.get("units_total", 0))),
        KPI("Scorable units", number(counts.get("units_scorable", 0))),
        KPI("Quarantined units", number(counts.get("units_quarantined", 0))),
        KPI("Runtime errors", number(counts.get("runtime_error_cases", 0))),
    )


def _english_table(summary: dict[str, Any], reference: dict[str, Any]) -> str:
    models = _reference_models(reference, "english")
    model_map = _reference_category_map(reference, "english")
    headers = "".join(
        f"<th>{escape(model.get('display_name', model.get('model_id', 'reference')))}</th>"
        for model in models
    )
    rows: list[str] = []
    for category, values in sorted(summary.get("categories", {}).items()):
        refs = model_map.get(category, {})
        reference_cells = []
        for model in models:
            model_id = str(model.get("model_id", ""))
            reference_cells.append(f"<td>{percent(refs.get(model_id, {}).get('accuracy'))}</td>")
        rows.append(
            f'<tr class="category-row" data-category="{escape(category)}" data-units="{int(values.get("units_total", 0))}">'
            f"<th>{escape(category)}</th>"
            f"<td><strong>{percent(values.get('accuracy'))}</strong>"
            f"<small>{int(values.get('units_scorable', 0)):,} / {int(values.get('units_total', 0)):,}</small></td>"
            f"{''.join(reference_cells)}</tr>"
        )
    return (
        '<div class="table-scroll"><table id="english-categories"><thead><tr><th>Category</th><th>Spokenform</th>'
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _multilingual_table(
    summary: dict[str, Any], reference: dict[str, Any], *, published: bool
) -> str:
    languages = sorted(summary.get("languages", {}))
    if not languages:
        languages = ["en", "de", "es", "fr", "it", "pt"]
    model_map = _reference_category_map(reference, "multilingual")
    categories = sorted(
        set(summary.get("categories", {})) | set(_reference_category_map(reference, "multilingual"))
    )
    headers = "".join(f"<th>{escape(language)}</th>" for language in languages)
    rows: list[str] = []
    for category in categories:
        cells: list[str] = []
        for language in languages:
            if published:
                value = model_map.get(category, {}).get(language, {}).get("accuracy")
                cells.append(f"<td>{percent(value)}</td>")
            else:
                value = summary.get("language_categories", {}).get(language, {}).get(category, {})
                cells.append(
                    f"<td><strong>{percent(value.get('accuracy'))}</strong>"
                    f"<small>{int(value.get('units_scorable', 0)):,} / {int(value.get('units_total', 0)):,}</small></td>"
                )
        rows.append(
            f'<tr class="category-row" data-category="{escape(category)}"><th>{escape(category)}</th>{"".join(cells)}</tr>'
        )
    title = "Published Async Flash v1.5 reference" if published else "Spokenform"
    return (
        f"<h3>{escape(title)}</h3>"
        f'<div class="table-scroll"><table><thead><tr><th>Category</th>{headers}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _sentence_failures(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in rows if row.get("error") or not row.get("speech_equivalent"))


def _unit_failures(units: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        row
        for row in units
        if row.get("outcome") not in {"correct-transform", "identity-preserved"}
    )


def _projection_status(row: dict[str, Any]) -> str:
    expected = bool(row.get("expected_mapping_ambiguous"))
    actual = bool(row.get("actual_mapping_ambiguous"))
    if expected and actual:
        return "expected and actual ambiguous"
    if expected:
        return "expected ambiguous"
    if actual:
        return "actual ambiguous"
    return "exact"


def _pill(text: str, *, warning: bool = False, info: bool = False) -> str:
    classes = ["pill"]
    if warning:
        classes.append("pill-warning")
    if info:
        classes.append("pill-info")
    return f'<span class="{" ".join(classes)}">{escape(text)}</span>'


def _projection_cell(label: str, value: object, *, ambiguous: bool) -> str:
    if ambiguous:
        return (
            '<div class="cell-stack">'
            f"{_pill('Ambiguous cross-unit projection', warning=True)}"
            f"<small>{escape(label)} is available in Details as diagnostic text only.</small>"
            "</div>"
        )
    return escape(value)


def _diagnostic_metadata(row: dict[str, Any], sentence: dict[str, Any] | None = None) -> str:
    payload = {
        "case_id": row.get("case_id"),
        "unit_id": row.get("unit_id"),
        "sentence_outcome": sentence.get("outcome") if sentence else None,
        "sentence_categories": sentence.get("categories") if sentence else None,
        "source_rules": row.get("source_rules"),
        "changed_stages": row.get("changed_stages"),
        "expected_mapping_ambiguous": row.get("expected_mapping_ambiguous"),
        "actual_mapping_ambiguous": row.get("actual_mapping_ambiguous"),
        "projected_expected": row.get("expected"),
        "projected_actual": row.get("actual"),
        "speech_wer": row.get("speech_wer"),
        "error": row.get("error"),
    }
    return details_block("Details", json_pre(payload))


def _sentence_failure_table(rows: tuple[dict[str, Any], ...]) -> str:
    filters = render_filter_controls(
        "async-sentence-failures",
        [
            FilterControl("text", "Search", mode="row-text", placeholder="Search rows"),
            FilterControl(
                "suite",
                "Suite",
                control="select",
                mode="exact",
                options=(("english", "english"), ("multilingual", "multilingual")),
            ),
            FilterControl(
                "language",
                "Language",
                control="select",
                mode="exact",
                options=tuple(
                    (language, language) for language in ("en", "de", "es", "fr", "it", "pt")
                ),
            ),
            FilterControl("category", "Category", placeholder="date"),
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
    rendered_rows: list[str] = []
    for row in rows:
        categories = ", ".join(str(value) for value in row.get("categories", ()))
        attrs = data_attributes(
            {
                "suite": row.get("suite", ""),
                "language": row.get("source_language", ""),
                "category": categories,
                "outcome": row.get("outcome", ""),
                "failure-family": row.get("failure_family", ""),
                "ownership": row.get("ownership", ""),
                "risk": row.get("risk_tier", ""),
                "speech-wer": row.get("speech_wer", 0),
            }
        )
        details = details_block(
            "Details",
            json_pre(
                {
                    "case_id": row.get("case_id"),
                    "categories": row.get("categories"),
                    "source_rules": row.get("source_rules"),
                    "changed_stages": row.get("changed_stages"),
                    "error": row.get("error"),
                }
            ),
        )
        rendered_rows.append(
            f'<tr data-filter-row="async-sentence-failures" {attrs}>'
            f"<td>{escape(row.get('case_id', ''))}</td>"
            f"<td>{escape(row.get('suite', ''))}</td>"
            f"<td>{escape(row.get('source_language', ''))}</td>"
            f"<td>{escape(categories)}</td>"
            f"<td>{escape(row.get('original_text', ''))}</td>"
            f"<td>{escape(row.get('expected', ''))}</td>"
            f"<td>{escape(row.get('actual', ''))}</td>"
            f"<td>{escape(row.get('outcome', ''))}</td>"
            f"<td>{decimal(row.get('speech_wer', 0))}</td>"
            f"<td>{escape(row.get('failure_family', ''))}</td>"
            f"<td>{escape(row.get('ownership', ''))}</td>"
            f"<td>{escape(row.get('risk_tier', ''))}</td>"
            f"<td>{details}</td>"
            "</tr>"
        )
    if not rendered_rows:
        rendered_rows.append(
            '<tr data-empty-for="async-sentence-failures"><td colspan="13">No sentence failures.</td></tr>'
        )
    return (
        "<h3>Sentence failures</h3>"
        "<p>Sentence expected and actual values below are the authoritative benchmark comparison.</p>"
        f"{filters}"
        '<p class="muted" data-empty-for="async-sentence-failures" hidden>No sentence rows match the current filters.</p>'
        '<div class="table-scroll"><table><thead><tr>'
        "<th>Case</th><th>Suite</th><th>Language</th><th>Categories</th><th>Sentence source</th>"
        "<th>Sentence expected</th><th>Sentence actual</th><th>Outcome</th><th>Speech WER</th>"
        "<th>Family</th><th>Ownership</th><th>Risk</th><th>Diagnostics</th>"
        f"</tr></thead><tbody>{''.join(rendered_rows)}</tbody></table></div>"
    )


def _unit_diagnostics_table(
    units: tuple[dict[str, Any], ...], sentence_by_case: dict[str, dict[str, Any]]
) -> str:
    filters = render_filter_controls(
        "async-unit-diagnostics",
        [
            FilterControl("text", "Search", mode="row-text", placeholder="Search rows"),
            FilterControl(
                "language",
                "Language",
                control="select",
                mode="exact",
                options=tuple(
                    (language, language) for language in ("en", "de", "es", "fr", "it", "pt")
                ),
            ),
            FilterControl("category", "Category", placeholder="time"),
            FilterControl(
                "outcome",
                "Outcome",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value)
                    for value in sorted(
                        {str(row.get("outcome", "")) for row in units if row.get("outcome")}
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
                            for row in units
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
                        {str(row.get("ownership", "")) for row in units if row.get("ownership")}
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
                        {str(row.get("risk_tier", "")) for row in units if row.get("risk_tier")}
                    )
                ),
            ),
            FilterControl(
                "projection-status",
                "Projection status",
                control="select",
                mode="exact",
                options=tuple(
                    (value, value) for value in sorted({_projection_status(row) for row in units})
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
    rendered_rows: list[str] = []
    for row in units:
        sentence = sentence_by_case.get(str(row.get("case_id")), {})
        projection_status = _projection_status(row)
        attrs = data_attributes(
            {
                "language": row.get("source_language", ""),
                "category": row.get("category", ""),
                "outcome": row.get("outcome", ""),
                "failure-family": row.get("failure_family", ""),
                "ownership": row.get("ownership", ""),
                "risk": row.get("risk_tier", ""),
                "projection-status": projection_status,
                "speech-wer": row.get("speech_wer", 0),
            }
        )
        rendered_rows.append(
            f'<tr data-filter-row="async-unit-diagnostics" {attrs}>'
            f"<td>{escape(row.get('unit_id', ''))}</td>"
            f"<td>{escape(row.get('source_language', ''))}</td>"
            f"<td>{escape(row.get('category', ''))}</td>"
            f"<td>{escape(row.get('source_text', ''))}</td>"
            f"<td>{escape(sentence.get('original_text', ''))}</td>"
            f"<td>{escape(sentence.get('expected', ''))}</td>"
            f"<td>{escape(sentence.get('actual', ''))}</td>"
            f"<td>{_projection_cell('Projected expected', row.get('expected', ''), ambiguous=bool(row.get('expected_mapping_ambiguous')))}</td>"
            f"<td>{_projection_cell('Projected actual', row.get('actual', ''), ambiguous=bool(row.get('actual_mapping_ambiguous')))}</td>"
            f"<td>{_pill(projection_status, warning='ambiguous' in projection_status, info='ambiguous' not in projection_status)}</td>"
            f"<td>{escape(row.get('outcome', ''))}</td>"
            f"<td>{decimal(row.get('speech_wer', 0))}</td>"
            f"<td>{escape(row.get('failure_family', ''))}</td>"
            f"<td>{escape(row.get('ownership', ''))}</td>"
            f"<td>{escape(row.get('risk_tier', ''))}</td>"
            f"<td>{_diagnostic_metadata(row, sentence)}</td>"
            "</tr>"
        )
    if not rendered_rows:
        rendered_rows.append(
            '<tr data-empty-for="async-unit-diagnostics"><td colspan="16">No unit diagnostics.</td></tr>'
        )
    return (
        "<h3>Unit diagnostics</h3>"
        "<p>Sentence expected and actual columns remain authoritative. Projected unit values are diagnostic only and become non-authoritative when a source edit crosses a unit boundary.</p>"
        f"{filters}"
        '<p class="muted" data-empty-for="async-unit-diagnostics" hidden>No unit rows match the current filters.</p>'
        '<div class="table-scroll"><table><thead><tr>'
        "<th>Unit</th><th>Language</th><th>Category</th><th>Unit source</th><th>Sentence source</th>"
        "<th>Sentence expected</th><th>Sentence actual</th><th>Projected expected</th><th>Projected actual</th>"
        "<th>Projection status</th><th>Outcome</th><th>Speech WER</th><th>Family</th><th>Ownership</th><th>Risk</th><th>Diagnostics</th>"
        f"</tr></thead><tbody>{''.join(rendered_rows)}</tbody></table></div>"
    )


def _failure_explorer(rows: tuple[dict[str, Any], ...], units: tuple[dict[str, Any], ...]) -> str:
    sentence_failures = _sentence_failures(rows)
    unit_failures = _unit_failures(units)
    sentence_by_case = {str(row.get("case_id")): row for row in rows}
    return (
        '<div class="subsection">'
        f"<p>{number(len(sentence_failures))} sentence failures and {number(len(unit_failures))} unit diagnostics are currently visible before local filters are applied.</p>"
        f"{_sentence_failure_table(sentence_failures)}"
        "</div>"
        '<div class="subsection">'
        f"{_unit_diagnostics_table(unit_failures, sentence_by_case)}"
        "</div>"
    )


def render_report(
    summary: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    units: Iterable[dict[str, Any]],
    reference: dict[str, Any],
    output: Path | str,
) -> Path:
    """Write one self-contained HTML report and return its path."""
    rows_tuple = tuple(rows)
    units_tuple = tuple(units)
    source = summary.get("source", {})
    metadata = {
        "run_id": summary.get("run_id"),
        "source_commit": summary.get("dataset_commit", reference.get("source_commit")),
        "source_files": source.get("files", {}),
        "configuration": summary.get("environment", {}).get("configuration", {}),
        "config_hash": summary.get("environment", {}).get("config_hash"),
        "spokenform_source_commit": summary.get("environment", {}).get("spokenform_source_commit"),
    }
    english_body = (
        '<div class="controls"><label>Search category <input id="category-search" type="search"></label>'
        f'<label>Minimum units <select id="min-units"><option>0</option><option>10</option><option>20</option><option selected>{DEFAULT_MIN_UNITS}</option></select></label>'
        '<label><input id="show-all" type="checkbox"> Show all categories</label></div>'
        f"{_english_table(summary, reference)}"
        "<script>"
        "function filterCategories(){"
        "const query=document.querySelector('#category-search').value.toLowerCase();"
        "const showAll=document.querySelector('#show-all').checked;"
        "const selected=Number(document.querySelector('#min-units').value)||0;"
        "document.querySelectorAll('#english-categories .category-row').forEach((row)=>{"
        "row.hidden=(!showAll&&Number(row.dataset.units)<selected)||!row.dataset.category.toLowerCase().includes(query);"
        "});"
        "}"
        "['#category-search','#min-units','#show-all'].forEach((selector)=>document.querySelector(selector).addEventListener('input',filterCategories));"
        "filterCategories();"
        "</script>"
    )
    sections = (
        Section("english", "English Benchmark", "English Benchmark", english_body, active=True),
        Section(
            "multilingual",
            "Multilingual",
            "Multilingual",
            "<p>Supported languages: en, de, es, fr, it, pt. Spokenform values preserve the source-to-runtime language mapping.</p>"
            f"{_multilingual_table(summary, reference, published=False)}"
            '<div class="subsection">'
            + notice(
                "Published reference values:",
                "upstream Async Flash v1.5 results are shown separately below and are not directly comparable to deterministic Spokenform scores.",
            )
            + f"{_multilingual_table(summary, reference, published=True)}"
            + "</div>",
        ),
        Section(
            "failures", "Failures", "Failure explorer", _failure_explorer(rows_tuple, units_tuple)
        ),
        Section(
            "metadata",
            "Run Metadata",
            "Run Metadata",
            f"{json_pre(metadata)}"
            + details_block(
                f"Sentence records ({len(rows_tuple)})",
                "<p>Sentence records are stored in <code>rows.jsonl</code> next to this report. "
                "Unit records are stored in <code>units.jsonl</code>.</p>",
            ),
        ),
    )
    subtitle = (
        f"Spokenform {summary.get('environment', {}).get('spokenform_version', 'unknown')} | "
        f"run {summary.get('run_id', 'unknown')} | profile {summary.get('profile', 'default')}"
    )
    intro_html = f"<p>Upstream commit: <code>{escape(metadata['source_commit'])}</code></p>"
    notices = (
        notice(
            "Methodology notice:",
            "Published TTS reference values use the upstream audio/LLM adjudication methodology. Spokenform is scored deterministically against normalized text. These percentages are displayed together for context and are not a like-for-like model ranking.",
        ),
    )
    return render_page(
        title="Async Voice TTS Normalization Benchmark",
        subtitle=subtitle,
        sections=sections,
        output=output,
        kpis=_kpis(summary),
        notices=notices,
        intro_html=intro_html,
    )


__all__ = ["DEFAULT_MIN_UNITS", "render_report"]
