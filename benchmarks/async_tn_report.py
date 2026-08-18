"""Render a self-contained static Async TN benchmark report."""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DEFAULT_MIN_UNITS = 30


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _percent(value: object) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "N/A"


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


def _kpis(summary: dict[str, Any]) -> str:
    counts = summary.get("counts", {})
    sentence = summary.get("sentence_metrics", {})
    unit = summary.get("unit_metrics", {})
    values = (
        ("Sentence speech-equivalent", _percent(sentence.get("speech_equivalent", 0) / sentence.get("total", 1) if sentence.get("total") else 0)),
        ("Unit speech-equivalent", _percent(unit.get("accuracy", 0))),
        ("Mean speech WER", f"{float(unit.get('mean_speech_wer', 0)):.4f}"),
        ("Total units", f"{int(counts.get('units_total', 0)):,}"),
        ("Scorable units", f"{int(counts.get('units_scorable', 0)):,}"),
        ("Quarantined units", f"{int(counts.get('units_quarantined', 0)):,}"),
        ("Runtime errors", f"{int(counts.get('runtime_error_cases', 0)):,}"),
    )
    return "\n".join(
        f'<div class="kpi"><strong>{_escape(value)}</strong><span>{_escape(label)}</span></div>'
        for label, value in values
    )


def _english_table(summary: dict[str, Any], reference: dict[str, Any]) -> str:
    models = _reference_models(reference, "english")
    model_map = _reference_category_map(reference, "english")
    headers = "".join(f"<th>{_escape(model.get('display_name', model.get('model_id', 'reference')))}</th>" for model in models)
    rows: list[str] = []
    for category, values in sorted(summary.get("categories", {}).items()):
        refs = model_map.get(category, {})
        reference_cells = []
        for model in models:
            model_id = model.get("model_id")
            reference_cells.append(f"<td>{_percent(refs.get(model_id, {}).get('accuracy'))}</td>")
        rows.append(
            f'<tr class="category-row" data-category="{_escape(category)}" data-units="{int(values.get("units_total", 0))}">'
            f"<th>{_escape(category)}</th>"
            f"<td><strong>{_percent(values.get('accuracy'))}</strong><small>{int(values.get('units_scorable', 0)):,} / {int(values.get('units_total', 0)):,}</small></td>"
            f"{''.join(reference_cells)}</tr>"
        )
    return (
        '<table id="english-categories"><thead><tr><th>Category</th><th>Spokenform</th>'
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _multilingual_table(summary: dict[str, Any], reference: dict[str, Any], *, published: bool) -> str:
    languages = sorted(summary.get("languages", {}))
    if not languages:
        languages = ["en", "de", "es", "fr", "it", "pt"]
    model_map = _reference_category_map(reference, "multilingual")
    categories = sorted(
        set(summary.get("categories", {}))
        | set(_reference_category_map(reference, "multilingual"))
    )
    headers = "".join(f"<th>{_escape(language)}</th>" for language in languages)
    rows: list[str] = []
    for category in categories:
        cells: list[str] = []
        for language in languages:
            if published:
                value = model_map.get(category, {}).get(language, {}).get("accuracy")
                cells.append(f"<td>{_percent(value)}</td>")
            else:
                value = summary.get("language_categories", {}).get(language, {}).get(category, {})
                cells.append(
                    f"<td><strong>{_percent(value.get('accuracy'))}</strong><small>{int(value.get('units_scorable', 0)):,} / {int(value.get('units_total', 0)):,}</small></td>"
                )
        rows.append(f'<tr class="category-row" data-category="{_escape(category)}"><th>{_escape(category)}</th>{"".join(cells)}</tr>')
    title = "Published Async Flash v1.5 reference" if published else "Spokenform"
    return f"<h3>{_escape(title)}</h3><table><thead><tr><th>Category</th>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _failure_table(units: Iterable[dict[str, Any]]) -> str:
    rows: list[str] = []
    for row in units:
        if row.get("outcome") in {"correct-transform", "identity-preserved"}:
            continue
        category = row.get("category", "")
        outcome = row.get("outcome", "")
        rows.append(
            f'<tr class="failure-row" data-suite="{_escape(row.get("suite", ""))}" data-language="{_escape(row.get("source_language", ""))}" data-category="{_escape(category)}" data-outcome="{_escape(outcome)}">'
            f"<td>{_escape(row.get('unit_id', ''))}</td><td>{_escape(row.get('source_text', ''))}</td><td>{_escape(category)}</td>"
            f"<td>{_escape(row.get('expected', ''))}</td><td>{_escape(row.get('actual', ''))}</td><td>{_escape(outcome)}</td>"
            f"<td>{_escape(row.get('failure_family', ''))}</td><td>{_escape(row.get('ownership', ''))}</td><td>{_escape(row.get('risk_tier', ''))}</td>"
            f"<td>{_escape(row.get('expected_mapping_ambiguous', False))} / { _escape(row.get('actual_mapping_ambiguous', False))}</td></tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="10">No selected failures.</td></tr>')
    return '<table id="failures"><thead><tr><th>Unit</th><th>Source</th><th>Category</th><th>Expected</th><th>Actual</th><th>Outcome</th><th>Family</th><th>Ownership</th><th>Risk</th><th>Mapping expected / actual</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"


def render_report(
    summary: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    units: Iterable[dict[str, Any]],
    reference: dict[str, Any],
    output: Path | str,
) -> Path:
    """Write one self-contained HTML report and return its path."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    html_document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Async Voice TTS Normalization Benchmark</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui,sans-serif; }} body {{ margin: 0; background: #f5f7fa; color: #17202a; }}
main {{ max-width: 1500px; margin: auto; padding: 2rem; }} header,.panel {{ background: white; border: 1px solid #d8dee8; border-radius: .6rem; padding: 1rem 1.25rem; margin-bottom: 1rem; }}
h1 {{ margin-top: 0; }} .muted {{ color: #657184; }} .notice {{ border-left: .35rem solid #d97706; background: #fff7ed; padding: 1rem; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: .7rem; }} .kpi {{ background: #eef4ff; padding: .8rem; border-radius: .4rem; }} .kpi strong,.kpi span {{ display:block; }} .kpi strong {{ font-size: 1.35rem; }} .kpi span {{ color:#526174; font-size:.85rem; }}
.tabs button {{ padding: .65rem 1rem; border: 1px solid #b9c4d2; background: #eef2f7; cursor: pointer; }} .tab {{ display:none; }} .tab.active {{ display:block; }}
table {{ border-collapse: collapse; width:100%; margin-top: .8rem; background:white; }} th,td {{ border:1px solid #d8dee8; padding:.45rem; text-align:left; vertical-align:top; }} th {{ background:#edf1f6; }} td small {{ display:block; color:#657184; }}
.controls {{ display:flex; flex-wrap:wrap; gap:.7rem; align-items:center; }} input,select {{ padding:.45rem; }} pre {{ overflow:auto; white-space:pre-wrap; word-break:break-word; }}
@media (prefers-color-scheme: dark) {{ body {{ background:#121820;color:#edf2f7; }} header,.panel,table {{ background:#1b2530; }} th {{ background:#293746; }} .notice {{ background:#3b2c15; }} .kpi {{ background:#20334d; }} }}
</style></head><body><main>
<header><h1>Async Voice TTS Normalization Benchmark</h1><p class="muted">Spokenform {_escape(summary.get('environment',{}).get('spokenform_version','unknown'))} | run {_escape(summary.get('run_id','unknown'))} | profile {_escape(summary.get('profile','default'))}</p><p>Upstream commit: <code>{_escape(metadata['source_commit'])}</code></p></header>
<section class="panel"><div class="kpis">{_kpis(summary)}</div></section>
<section class="panel notice"><strong>Methodology notice:</strong> Published TTS reference values use the upstream audio/LLM adjudication methodology. Spokenform is scored deterministically against normalized text. These percentages are displayed together for context and are not a like-for-like model ranking.</section>
<nav class="tabs" aria-label="Report sections"><button data-tab="english">English Benchmark</button><button data-tab="multilingual">Multilingual</button><button data-tab="failures">Failures</button><button data-tab="metadata">Run Metadata</button></nav>
<section id="english" class="tab active panel"><h2>English Benchmark</h2><div class="controls"><label>Search category <input id="category-search" type="search"></label><label>Minimum units <select id="min-units"><option>0</option><option>10</option><option>20</option><option selected>{DEFAULT_MIN_UNITS}</option><option value="custom">Custom</option></select></label><label><input id="show-all" type="checkbox"> Show all categories</label></div>{_english_table(summary, reference)}</section>
<section id="multilingual" class="tab panel"><h2>Multilingual</h2><p>Supported languages: en, de, es, fr, it, pt. Spokenform values preserve the source-to-runtime language mapping.</p>{_multilingual_table(summary, reference, published=False)}<div class="notice"><strong>Published reference values:</strong> upstream Async Flash v1.5 results are shown separately below and are not directly comparable to deterministic Spokenform scores.</div>{_multilingual_table(summary, reference, published=True)}</section>
<section id="failures" class="tab panel"><h2>Failure explorer</h2><div class="controls"><label>Search <input id="failure-search" type="search"></label><label>Outcome <input id="failure-outcome" type="search"></label><label>Category <input id="failure-category" type="search"></label></div>{_failure_table(units_tuple)}</section>
<section id="metadata" class="tab panel"><h2>Run metadata</h2><pre>{_escape(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))}</pre><details><summary>Sentence records ({len(rows_tuple)})</summary><p>Sentence records are stored in <code>rows.jsonl</code> next to this report. Unit records are stored in <code>units.jsonl</code>.</p></details></section>
<script>
const tabs=[...document.querySelectorAll('[data-tab]')]; const sections=[...document.querySelectorAll('.tab')];
tabs.forEach(button=>button.addEventListener('click',()=>{{sections.forEach(section=>section.classList.toggle('active',section.id===button.dataset.tab));}}));
function filterCategories(){{const query=document.querySelector('#category-search').value.toLowerCase(); const showAll=document.querySelector('#show-all').checked; const selected=Number(document.querySelector('#min-units').value)||0; document.querySelectorAll('#english-categories .category-row').forEach(row=>{{row.hidden=(!showAll&&Number(row.dataset.units)<selected)||!row.dataset.category.toLowerCase().includes(query);}});}}
['#category-search','#min-units','#show-all'].forEach(selector=>document.querySelector(selector).addEventListener('input',filterCategories));
function filterFailures(){{const search=document.querySelector('#failure-search').value.toLowerCase(); const outcome=document.querySelector('#failure-outcome').value.toLowerCase(); const category=document.querySelector('#failure-category').value.toLowerCase(); document.querySelectorAll('.failure-row').forEach(row=>{{row.hidden=!row.textContent.toLowerCase().includes(search)||!row.dataset.outcome.includes(outcome)||!row.dataset.category.includes(category);}});}}
['#failure-search','#failure-outcome','#failure-category'].forEach(selector=>document.querySelector(selector).addEventListener('input',filterFailures)); filterCategories();
</script></main></body></html>'''
    output_path.write_text(html_document, encoding="utf-8")
    return output_path


__all__ = ["DEFAULT_MIN_UNITS", "render_report"]
