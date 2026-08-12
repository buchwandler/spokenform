# Benchmarks

## PolyNorm benchmark

`python -m benchmarks.polynorm --accept-license` runs the diagnostic adapter for
the five locales shared by PolyNorm-Bench and Spokenform. The upstream data is
licensed CC BY-NC-ND 4.0, so downloading requires the explicit
`--accept-license` flag. Data is fetched from the pinned upstream commit and
stored under `.cache/polynorm-bench/<commit>/`; it is never packaged or
committed.

Use `--offline` after the cache has been populated. The adapter also supports
`--locale`, `--category`, `--case`, `--limit`, `--refresh`, `--download-only`,
`--profile default|extended`, `--normalize-literals`, and `--show-failures all`.
Reports are written to
`benchmark-results/polynorm/<run-id>/`. `summary.json` contains metrics and
metadata only; the JSONL and Markdown failure reports contain source text and
remain local.

The default profile calls `prepare(..., normalize_literals=False)` and treats
URL/email/version rows as protected ownership. The extended profile calls
`normalize_literals=True` and measures optional literal verbalization. Keep
the profile field when comparing reports.

PolyNorm is a discovery tool, not a normal CI or release gate. The benchmark
does not make unsupported PolyNorm locales part of Spokenform's public API.

Fresh runs record the resolved Spokenform, `abbr2words`, and `num2words`
versions, PolyNorm dataset commit, locale mapping, Python version, and the
available case count. The pinned snapshot currently contains 2,680 overlap
cases; reports use the available count rather than assuming every locale has
the same number of rows.

See the detailed [PolyNorm documentation](../docs/polynorm.md).

## Proteno benchmark

`python -m benchmarks.proteno --accept-license` runs the pinned English and
Spanish Proteno diagnostic benchmark. Data is cached under
`.cache/proteno/<commit>/`; reports are written under
`benchmark-results/proteno/<run-id>/`. Use `--profile extended` or
`--normalize-literals` for the opt-in literal profile. The external data is
never packaged or committed. See the detailed [Proteno documentation](../docs/proteno.md).
