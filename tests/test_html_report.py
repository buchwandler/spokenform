from __future__ import annotations

from benchmarks.html_report import (
    KPI,
    FilterControl,
    Section,
    data_attributes,
    render_filter_controls,
    render_page,
)


def test_shared_report_shell_is_self_contained_and_wires_filters(tmp_path):
    controls = render_filter_controls(
        "demo",
        [
            FilterControl("text", "Search", mode="row-text", placeholder="Search rows"),
            FilterControl(
                "status",
                "Status",
                control="select",
                mode="exact",
                options=(("open", "open"), ("closed", "closed")),
            ),
        ],
    )
    attrs = data_attributes({"status": "open", "text": "alpha"})
    body = (
        f"{controls}"
        "<table><tbody>"
        f'<tr data-filter-row="demo" {attrs}><td>alpha</td></tr>'
        "</tbody></table>"
        '<p data-empty-for="demo" hidden>No rows.</p>'
    )
    path = render_page(
        title="Demo report",
        subtitle="local only",
        sections=[Section("overview", "Overview", "Overview", body, active=True)],
        output=tmp_path / "report.html",
        kpis=[KPI("Rows", "1")],
        intro_html="<p>self contained</p>",
    )
    text = path.read_text(encoding="utf-8")
    assert 'data-table-filters="demo"' in text
    assert 'data-row-count-for="demo"' in text
    assert 'data-filter-row="demo"' in text
    assert "https://" not in text
    assert "cdn" not in text.lower()


def test_shared_report_shell_escapes_data_attributes():
    attrs = data_attributes({"status": '"quoted" & <tag>'})
    assert "&quot;quoted&quot; &amp; &lt;tag&gt;" in attrs
