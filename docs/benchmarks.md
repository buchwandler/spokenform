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

Japanese, Korean, and Chinese runtime support is regression-tested but is not part of the current seven-language PolyNorm or kokorog2p parity scope without a dedicated benchmark adapter and corpus.

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

## Spokenform Gold

Run the pinned Gold release diagnostic benchmark with:

```bash
python -m benchmarks.spokenform_gold \
  --split corpus \
  --accept-upstream-licenses \
  --report html
```

The consumer reads the exact `v0.1.0-exp.2` release asset pinned in
`benchmarks/spokenform_gold_release.json`. It never rebuilds Gold data from a
source checkout and never selects the latest GitHub release dynamically. The
pin contains the release tag, asset SHA-256, manifest SHA-256, target commit,
and matching runtime source ref. The first online run downloads and verifies the
release zip and matching runtime source under `.cache/spokenform-gold/`. The
v2 corpus is unsplit and contains 20,037 public release records, including 1,978
external-reference records and 18,059 embedded records.

Use `--offline` after the cache is populated, `--refresh` only after an intentional
pin update, `--download-only` to populate without evaluation, `--cache-dir` or
`--source-cache-dir` to relocate release or external-source caches, `--gold-root`
for an extracted release directory containing `manifest.json`, `--split corpus`,
`--mode canonical|accepted`, and `--report none` to disable HTML. Passing a source
checkout to `--gold-root` is rejected with a targeted diagnostic.

Full corpus runs require `--accept-upstream-licenses` before source hydration. The
benchmark fails before scoring if the flag is absent, evaluates all 20,037 release
records, and records release identity and coverage in `summary.json` and the
self-contained `report.html`. Use `--offline` to guarantee that source hydration
performs no network access.

## Lexhint A/B comparison

Compare the existing provider-free configuration with the same configuration plus a pinned Lexhint runtime artifact. Keep Spokenform, abbr2words, language, profile, and benchmark inputs fixed. Record the Spokenform commit/version, abbr2words version, Lexhint package version, dataset version, schema version, variant, language, and profile.

Review URL, version, identifier, and sports families separately. The provider-free run is the compatibility baseline. Lexhint is successful only when URL rendering improves and contextual true positives increase without material IP, date, reference, or score false positives. Do not use an unpinned latest dataset for release comparisons.
