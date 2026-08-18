# Benchmarks

The benchmark suites are diagnostic and release-supporting tools, not a
replacement for the semantic regression and false-positive tests.

```{toctree}
:maxdepth: 1

polynorm
proteno
google_tn
async_tn
```

The benchmark ownership and release policy are documented in
[`benchmarks/OWNERSHIP.md`](https://github.com/buchwandler/spokenform/blob/main/benchmarks/OWNERSHIP.md). PolyNorm and Proteno
measure specialized external-corpus behavior; Google TN is an offline English
text-normalization comparison; Async TN is a pinned English and six-language
annotated TTS-normalization diagnostic. Their data and reports live under
`benchmarks/` and should be interpreted with the safety and quarantine guidance
in the ownership document. See [Async TN](async_tn.md) for its mapping,
methodology, and static dashboard contract.

Async TN, PolyNorm, and Proteno now each write a self-contained local
`report.html` dashboard by default. These dashboards reuse a shared static HTML
shell, keep dataset/runtime strings escaped, expose local KPI and diagnostic
views, and can be disabled with `--report none` when only the JSONL/Markdown
artifacts are needed.

All four benchmark CLIs also support a diagnostic `--candidate-oracle` mode.
It keeps runtime normalization unchanged, enumerates bounded alternative
structured-candidate selections, writes per-run `oracle_summary.json`, and can
be used to measure selector headroom before attempting any learned ranking or
selection project.
