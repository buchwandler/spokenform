"""Shared helpers for self-contained benchmark HTML reports."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class KPI:
    """One KPI card rendered near the top of a report."""

    label: str
    value: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class Section:
    """One tabbed report section."""

    section_id: str
    tab_label: str
    title: str
    body_html: str
    active: bool = False


@dataclass(frozen=True, slots=True)
class FilterControl:
    """A declarative row-filter control."""

    key: str
    label: str
    control: str = "search"
    mode: str = "contains"
    placeholder: str = ""
    options: tuple[tuple[str, str], ...] = ()
    step: str = "any"


def escape(value: object) -> str:
    """Escape a value for HTML."""
    return html.escape(str(value), quote=True)


def percent(value: Any, *, digits: int = 2) -> str:
    """Render a fractional value as a percentage."""
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "N/A"


def decimal(value: Any, *, digits: int = 4) -> str:
    """Render a numeric value with a fixed number of decimal digits."""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "N/A"


def number(value: Any) -> str:
    """Render an integer-like value with grouping."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def data_attributes(values: dict[str, object]) -> str:
    """Render ``data-*`` attributes from a mapping."""

    def _value(raw: object) -> str:
        if raw is None:
            return ""
        if isinstance(raw, bool):
            return "true" if raw else "false"
        return str(raw)

    return " ".join(
        f'data-{escape(key.replace("_", "-"))}="{escape(_value(value))}"'
        for key, value in values.items()
    )


def json_pre(payload: dict[str, Any]) -> str:
    """Render JSON metadata inside a ``pre`` block."""
    return f"<pre>{escape(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))}</pre>"


def details_block(summary: str, body_html: str) -> str:
    """Render a ``details`` block."""
    return f"<details><summary>{escape(summary)}</summary>{body_html}</details>"


def notice(title: str, body: str) -> str:
    """Render a highlighted notice panel."""
    return f'<section class="panel notice"><strong>{escape(title)}</strong> {body}</section>'


def render_kpis(kpis: tuple[KPI, ...] | list[KPI]) -> str:
    """Render the KPI panel."""
    if not kpis:
        return ""
    cards = []
    for item in kpis:
        detail = f"<small>{escape(item.detail)}</small>" if item.detail else ""
        cards.append(
            '<div class="kpi">'
            f"<strong>{escape(item.value)}</strong>"
            f"<span>{escape(item.label)}</span>"
            f"{detail}"
            "</div>"
        )
    return f'<section class="panel"><div class="kpis">{"".join(cards)}</div></section>'


def render_filter_controls(
    table_id: str,
    controls: tuple[FilterControl, ...] | list[FilterControl],
    *,
    count_label: str = "Visible rows",
) -> str:
    """Render filter controls for one table."""
    parts = [f'<div class="controls report-filters" data-table-filters="{escape(table_id)}">']
    for control in controls:
        input_html: str
        if control.control == "select":
            options = ['<option value="">All</option>']
            options.extend(
                f'<option value="{escape(value)}">{escape(label)}</option>'
                for value, label in control.options
            )
            input_html = (
                f'<select data-filter-key="{escape(control.key)}" '
                f'data-filter-mode="{escape(control.mode)}">'
                f"{''.join(options)}</select>"
            )
        elif control.control == "number":
            input_html = (
                f'<input type="number" step="{escape(control.step)}" '
                f'placeholder="{escape(control.placeholder)}" '
                f'data-filter-key="{escape(control.key)}" '
                f'data-filter-mode="{escape(control.mode)}">'
            )
        else:
            input_html = (
                f'<input type="search" placeholder="{escape(control.placeholder)}" '
                f'data-filter-key="{escape(control.key)}" '
                f'data-filter-mode="{escape(control.mode)}">'
            )
        parts.append(f"<label>{escape(control.label)} {input_html}</label>")
    parts.append(
        f'<span class="row-count">{escape(count_label)}: '
        f'<strong data-row-count-for="{escape(table_id)}">0 / 0</strong></span>'
    )
    parts.append("</div>")
    return "".join(parts)


_STYLE = """
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { margin: 0; background: #f5f7fa; color: #17202a; }
main { max-width: 1600px; margin: auto; padding: 2rem; }
header, .panel { background: white; border: 1px solid #d8dee8; border-radius: .6rem; padding: 1rem 1.25rem; margin-bottom: 1rem; }
h1, h2, h3, h4 { margin-top: 0; }
.muted { color: #657184; }
.notice { border-left: .35rem solid #d97706; background: #fff7ed; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .7rem; }
.kpi { background: #eef4ff; padding: .8rem; border-radius: .4rem; }
.kpi strong, .kpi span, .kpi small { display: block; }
.kpi strong { font-size: 1.35rem; }
.kpi span, .kpi small { color: #526174; }
.tabs { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: 1rem; }
.tabs button { padding: .65rem 1rem; border: 1px solid #b9c4d2; border-radius: .4rem; background: #eef2f7; cursor: pointer; }
.tabs button.active { background: #20334d; color: white; border-color: #20334d; }
.tab { display: none; }
.tab.active { display: block; }
table { border-collapse: collapse; width: 100%; margin-top: .8rem; background: white; }
th, td { border: 1px solid #d8dee8; padding: .45rem; text-align: left; vertical-align: top; }
th { background: #edf1f6; }
td small, .cell-stack small { display: block; color: #657184; }
.cell-stack > * + * { margin-top: .3rem; }
.controls { display: flex; flex-wrap: wrap; gap: .7rem; align-items: end; margin-bottom: .8rem; }
.controls label { display: flex; flex-direction: column; gap: .2rem; font-size: .95rem; }
.controls input, .controls select { padding: .45rem; min-width: 10rem; }
.row-count { margin-left: auto; font-weight: 600; }
.table-scroll { overflow-x: auto; }
.pill { display: inline-block; border-radius: 999px; padding: .15rem .55rem; font-size: .8rem; font-weight: 600; background: #edf1f6; }
.pill-warning { background: #fff1c2; color: #7c4a03; }
.pill-info { background: #dbeafe; color: #0f4c81; }
details summary { cursor: pointer; font-weight: 600; }
pre { overflow: auto; white-space: pre-wrap; word-break: break-word; }
.two-column { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.subsection + .subsection { margin-top: 1rem; }
@media (prefers-color-scheme: dark) {
  body { background: #121820; color: #edf2f7; }
  header, .panel, table { background: #1b2530; }
  th { background: #293746; }
  .notice { background: #3b2c15; }
  .kpi { background: #20334d; }
  .tabs button { background: #1d2834; color: #edf2f7; border-color: #334355; }
  .tabs button.active { background: #4b7bb1; border-color: #4b7bb1; }
  .pill { background: #2b3a49; color: #edf2f7; }
  .pill-warning { background: #624a00; color: #fff2c7; }
  .pill-info { background: #17365d; color: #dbeafe; }
}
"""


_SCRIPT = """
const tabs = [...document.querySelectorAll('[data-tab-target]')];
const sections = [...document.querySelectorAll('.tab')];
function activateTab(targetId) {
  sections.forEach((section) => {
    section.classList.toggle('active', section.id === targetId);
  });
  tabs.forEach((button) => {
    button.classList.toggle('active', button.dataset.tabTarget === targetId);
  });
}
tabs.forEach((button) => {
  button.addEventListener('click', () => activateTab(button.dataset.tabTarget));
});
if (tabs.length && !tabs.some((button) => button.classList.contains('active'))) {
  activateTab(tabs[0].dataset.tabTarget);
}

function normalize(value) {
  return (value || '').toString().toLowerCase();
}

function tableRows(tableId) {
  return [...document.querySelectorAll(`[data-filter-row="${tableId}"]`)];
}

function updateCount(tableId, visible, total) {
  document.querySelectorAll(`[data-row-count-for="${tableId}"]`).forEach((node) => {
    node.textContent = `${visible} / ${total}`;
  });
  document.querySelectorAll(`[data-empty-for="${tableId}"]`).forEach((node) => {
    node.hidden = visible !== 0;
  });
}

function applyTableFilters(container) {
  const tableId = container.dataset.tableFilters;
  const rows = tableRows(tableId);
  const controls = [...container.querySelectorAll('[data-filter-key]')];
  let visible = 0;
  rows.forEach((row) => {
    let keep = true;
    for (const control of controls) {
      const value = normalize(control.value).trim();
      if (!value) {
        continue;
      }
      const key = control.dataset.filterKey;
      const mode = control.dataset.filterMode || 'contains';
      if (mode === 'row-text') {
        keep = normalize(row.textContent).includes(value);
      } else if (mode === 'exact') {
        keep = normalize(row.getAttribute(`data-${key}`)).trim() === value;
      } else if (mode === 'min-number') {
        const rowValue = Number.parseFloat(row.getAttribute(`data-${key}`) || '');
        const filterValue = Number.parseFloat(value);
        keep = Number.isFinite(rowValue) && Number.isFinite(filterValue) && rowValue >= filterValue;
      } else {
        keep = normalize(row.getAttribute(`data-${key}`)).includes(value);
      }
      if (!keep) {
        break;
      }
    }
    row.hidden = !keep;
    if (keep) {
      visible += 1;
    }
  });
  updateCount(tableId, visible, rows.length);
}

document.querySelectorAll('[data-table-filters]').forEach((container) => {
  const handler = () => applyTableFilters(container);
  container.querySelectorAll('[data-filter-key]').forEach((control) => {
    control.addEventListener('input', handler);
    control.addEventListener('change', handler);
  });
  handler();
});
"""


def render_page(
    *,
    title: str,
    subtitle: str,
    sections: tuple[Section, ...] | list[Section],
    output: Path | str,
    kpis: tuple[KPI, ...] | list[KPI] = (),
    notices: tuple[str, ...] | list[str] = (),
    intro_html: str = "",
) -> Path:
    """Write one self-contained benchmark HTML report."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected_sections = tuple(sections)
    if not selected_sections:
        raise ValueError("at least one report section is required")
    if not any(section.active for section in selected_sections):
        selected_sections = (replace(selected_sections[0], active=True),) + tuple(
            selected_sections[1:]
        )
    nav_html = "".join(
        f'<button data-tab-target="{escape(section.section_id)}"'
        f' class="{"active" if section.active else ""}">{escape(section.tab_label)}</button>'
        for section in selected_sections
    )
    section_html = "".join(
        f'<section id="{escape(section.section_id)}" class="tab{" active" if section.active else ""} panel">'
        f"<h2>{escape(section.title)}</h2>"
        f"{section.body_html}"
        "</section>"
        for section in selected_sections
    )
    html_document = (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f"<style>{_STYLE}</style>"
        "</head><body><main>"
        f'<header><h1>{escape(title)}</h1><p class="muted">{escape(subtitle)}</p>{intro_html}</header>'
        f"{render_kpis(list(kpis))}"
        f"{''.join(notices)}"
        f'<nav class="tabs" aria-label="Report sections">{nav_html}</nav>'
        f"{section_html}"
        f"<script>{_SCRIPT}</script>"
        "</main></body></html>"
    )
    output_path.write_text(html_document, encoding="utf-8")
    return output_path


__all__ = [
    "FilterControl",
    "KPI",
    "Section",
    "data_attributes",
    "decimal",
    "details_block",
    "escape",
    "json_pre",
    "notice",
    "number",
    "percent",
    "render_filter_controls",
    "render_kpis",
    "render_page",
]
