# Async Voice TTS Normalization Benchmark

Async TN is a diagnostic adapter for the Async Voice AI Text-to-Speech
Normalization Benchmark. It evaluates Spokenform deterministically against the
upstream normalized text. It does not change normalization behavior and does
not use upstream category labels as runtime hints.

## Source and license

The adapter uses the English `data/sentences.json` and multilingual
`data/multilingual-sentences.json` files from the Apache-2.0 Hugging Face Space:

<https://huggingface.co/spaces/async-vocie-ai/text-to-speech-normalization-benchmark>

The source revision is pinned to
`516dfbf54c8f85db865b65de4272b1f4280ad1dd`. Raw URLs include this revision, and
run metadata records the SHA-256 and byte size of every downloaded source and
reference file. The full corpus is never packaged or committed.

## Suites and languages

The English suite maps `en` to Spokenform `en_US`. The multilingual suite
supports `en`, `de`, `es`, `fr`, `it`, and `pt`, with `en` mapped to `en_US` and
the other codes mapped to their Spokenform language. Both source and resolved
language are retained in every result.

## Commands

```bash
python -m benchmarks.async_tn --suite english
python -m benchmarks.async_tn --suite multilingual
python -m benchmarks.async_tn --suite multilingual --language de
python -m benchmarks.async_tn --suite english --category date
python -m benchmarks.async_tn --suite all --offline
python -m benchmarks.async_tn --suite all --profile extended --show-failures semantic
python -m benchmarks.async_tn --download-only
```

Use `--case`, `--limit`, `--speech-wer-threshold`, `--report none`,
`--normalize-literals`, `--refresh`, and `--cache-dir` for focused runs.
`--language` is a multilingual filter and is rejected for the English-only
suite. `--offline` never makes a network request, and cannot be combined with
`--refresh`.

## Cache and result files

Data is cached under:

```text
.cache/async-tn/516dfbf54c8f85db865b65de4272b1f4280ad1dd/
```

`metadata.json` records the source repository, commit, license, hashes, and
sizes. Downloaded files are validated and replaced atomically. A cache miss in
offline mode is an error.

Each run writes `benchmark-results/async-tn/<run-id>/` containing:

- `summary.json`, counts, metrics, diagnostics, configuration, and provenance;
- `rows.jsonl`, one sentence record per evaluated case;
- `units.jsonl`, one annotated unit record per source unit;
- `failures.jsonl` and `failures.md`, triage-oriented failure records;
- `exclusions.jsonl`, quarantined source records;
- `reference.json`, pinned upstream published TTS reference values;
- `report.html`, a self-contained static dashboard.

## Metrics and mapping

Sentence and unit records include literal exactness, speech exactness, speech
equivalence, and word error rate from `benchmarks.text_metrics`. Category and
language reports expose total, scorable, correct, incorrect, quarantined, and
runtime-error denominators. Percentages are never shown without their counts.
Sentence exactness and the `all_units_correct` unit result remain separate.

The source annotation is mapped into the expected full sentence using
Spokenform's `OffsetMap` and deterministic diff replacements. The actual unit
is mapped from the single `prepare()` result for the complete sentence. A
replacement crossing a unit boundary is marked `mapping-ambiguous` rather than
being assigned to a unit by heuristic substring matching.

Source offsets are validated when provided. Missing offsets are resolved by
exact text in unit order. Missing, invalid, overlapping, repeated ambiguous, or
unsupported records are quarantined with explicit reason codes. Unknown
category strings are retained and included in machine-readable aggregates.
The dashboard's default category presentation threshold is 30 units only; it
does not remove low-frequency categories from result files.

## Profiles and safety

The default profile uses conservative Spokenform behavior with literal
normalization disabled. `extended` is opt-in and enables the existing extended
literal behavior. The benchmark calls `prepare()` once per sentence and never
passes an upstream category or other benchmark-only oracle to the runtime.
Ownership, risk tier, provenance, and failure-family fields are diagnostic
metadata. Benchmark failures do not authorize broad runtime rule changes.

## Dashboard

`report.html` opens directly from a filesystem path. It has English,
multilingual, failures, and metadata views, category search and threshold
controls, language/category/family/ownership/risk failure filters, live
visible-row counts, source-stage details, and a reproducibility panel. It
contains no CDN, external font, remote image, or server dependency. Dataset
and runtime strings are HTML-escaped.

The failure explorer separates authoritative sentence failures from unit-level
diagnostics. Sentence rows always use sentence-level source, expected, and
actual text. Unit rows expose projected expected and projected actual text as
diagnostic views only. When a source edit crosses a unit boundary, the unit row
is marked `mapping-ambiguous`; the raw projected text stays available in the
diagnostic details, but it is never presented as an authoritative unit target
or unit output and the unit remains unscorable.

The published reference values come from the pinned overview/category JSON and
represent the upstream audio/LLM judge methodology. Spokenform values are
computed against normalized text. The report displays these values separately
for context and never computes a mixed-method winner or ranking.

## Comparing runs

```bash
python -m benchmarks.async_tn_compare \
  benchmark-results/async-tn/run-a \
  benchmark-results/async-tn/run-b
```

Comparison requires matching benchmark, repository, commit, source file hashes,
suite, language mapping, profile, and configuration hash. It reports sentence
and unit failures, language/category deltas, stable case and unit IDs, and new,
resolved, and remaining quarantines. Use `--allow-incompatible` only for an
intentional exploratory comparison; the result records that override.

## Baselines and policy

Baseline commands are run after implementation against the pinned source. Keep
only small policy-approved summary or documentation artifacts. Do not commit the
downloaded corpus, full source-bearing failure data, or generated reports unless
repository policy explicitly requests them. Async TN is diagnostic and is not a
replacement for the false-positive safety suite or existing benchmark gates.
