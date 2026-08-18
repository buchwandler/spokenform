# Proteno benchmark

The Proteno benchmark evaluates Spokenform against the Amazon Science Proteno
English and Spanish text-normalization data. It is a local diagnostic tool for
finding normalization and identity-safety gaps, not a release gate.

The adapter is pinned to commit
`8839501abaf50eeccbe21a2397cefa118eae9660`. The English and Spanish releases
contain 24,760 and 4,791 sentence pairs respectively. Both language-specific
licenses are Creative Commons Attribution-ShareAlike 3.0 Unported. Downloading
requires explicit acceptance:

```bash
python -m benchmarks.proteno --accept-license --download-only
```

Data is stored in `.cache/proteno/<commit>/English/` and
`.cache/proteno/<commit>/Spanish/`. Each downloaded file is checked against its
expected size and pinned Git blob SHA. The restricted loader accepts only the
documented primitive list shapes, plus the pinned English `numpy.str_` scalar
representation, which is converted to native text. Proteno files are not copied
to `tests/data/`, packaged, or committed.

## Running

After the cache is populated, offline runs do not access the network:

```bash
python -m benchmarks.proteno --offline
python -m benchmarks.proteno --offline --language en
python -m benchmarks.proteno --offline --language es
python -m benchmarks.proteno --offline --split test
python -m benchmarks.proteno --offline --language en --limit 100
python -m benchmarks.proteno --offline --case en:00481 --show-failures all
python -m benchmarks.proteno --offline --speech-wer-threshold 0.5
python -m benchmarks.proteno --offline --report html
```

Use `--refresh` to redownload selected pinned files. `--cache-dir` and
`--results-dir` relocate the cache and local reports. The default split is
`all`; `train` is the first `int(total * 0.60)` rows (floor rounding), and
`test` is the remaining rows. Case IDs use the absolute one-based upstream row,
for example `en:00481`, so filtering does not renumber cases.

`--show-failures all` prints the compact `failures.md` index; open its links to
inspect the bounded detail shards.

Use `--speech-wer-threshold VALUE` to persist only failure entries whose word
error rate is strictly greater than `VALUE`. The option filters
`failures.jsonl` and the Markdown failure shards only; summary metrics and
evaluated-case counts still cover the complete run. With no threshold, all
current failure entries are stored.

Spokenform uses `en_US` for Proteno English and generic `es` for Proteno Spanish,
with `use_spacy=False` and `symbol_mode="remove"` recorded in the environment
metadata. Proteno's normalized target presentation requires residual sign
removal; this is benchmark configuration and does not change Spokenform's
normal `symbol_mode="none"` default.

## Spanish projection and exclusions

Spanish `<error what="NORMALIZED">SOURCE</error>` annotations contribute the
`what` value to expected spoken text; the inner source form is ignored. Entire
`<lang>...</lang>` foreign-language spans are removed. Unknown, malformed, or
incomplete tags are adapter errors and are recorded in `excluded.jsonl` rather
than silently stripped. URL/web-address cases that remain after projection are
excluded with reason `upstream_ignored_url` because the upstream README says
they were ignored for training.

## Reports and comparison

Reports are written to `benchmark-results/proteno/<UTC-run-id>/`:

- `summary.json` contains metadata and aggregate metrics only; it contains no
  corpus sentences.
- `failures.jsonl` contains the complete machine-readable failure report.
- `failures.md` is a small index linking to bounded, source-bearing Markdown
  shards grouped by language and case kind. Each shard is capped at 1 MiB and
  contains local source, expected, actual, WER, and provenance evidence.
- `excluded.jsonl` records adapter exclusions separately from Spokenform output.
- `report.html` is a self-contained local dashboard with KPI, language,
  normalization/identity, language × case-kind, diagnostics, failure, metadata,
  and optional oracle views. Use `--report none` to skip HTML generation.

Metrics separate normalization cases from identity cases. Semantic comparison
uses speech-token exactness plus the localized-letter equivalence diagnostic;
literal comparison and word error rate are also reported. `unchanged` therefore
means a likely miss for normalization cases but is generally desirable for
identity cases.

Each summary also exposes `diagnostic_aggregates` by primary rule, failure
phase, ownership, and ambiguity family, plus an explicit per-row `outcome`
(`semantic-mismatch`, `presentation-only`, `protected-by-profile`,
`questionable-target`, `malformed-ground-truth`, or `runtime-error`). The local
`PROTENO_QUARANTINE` table is intentionally separate from downloaded data and
is populated only after a concrete source/target inconsistency is reviewed.

Compare two local runs with:

```bash
python -m benchmarks.proteno_compare \
    benchmark-results/proteno/<before> \
    benchmark-results/proteno/<after>
```

The comparison reports aggregate deltas and `resolved`, `new_failures`, and
`remaining` stable case-ID sets. Source-bearing reports should remain local and
must not be committed.

## Benchmark profiles

Proteno reports default to `normalize_literals=False`. The extended profile is
opt-in through `--profile extended` or `--normalize-literals` and is reported
separately so protected literal behavior is not mixed into the conservative
default score. Extended runs use conservative unknown-acronym handling and
registered source-letter spelling; contextual long-number normalization is an
explicit experiment, never the public default. The caller-level aggressive
combination (`spell_unknown` plus cardinal long numbers) is not a release
profile.

See [the benchmark ownership table](https://github.com/buchwandler/spokenform/blob/main/benchmarks/OWNERSHIP.md) for the
safety, owned, extended-candidate, protected, downstream, unsupported, and
quarantine gates.
