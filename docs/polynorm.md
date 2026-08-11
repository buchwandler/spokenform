# PolyNorm diagnostic benchmark

Spokenform's PolyNorm adapter evaluates the overlap between the external
Apple PolyNorm-Bench corpus and the seven base languages supported by
Spokenform. The overlap is `de-DE`, `en-US`, `es-MX`, `fr-FR`, and `it-IT`;
the default run derives its case count from the selected cached files because
upstream locale files may differ in length. PolyNorm BCP-47 tags are translated
to regional Spokenform identifiers only inside the benchmark adapter; they are
not a Spokenform API convention.

The source is pinned to dataset commit
`f3c67e047bea6b7c40bc2466c0fdaad51d8ce67d` in
`apple/ml-speech-polynorm-bench`. The dataset is CC BY-NC-ND 4.0. The first
download requires an explicit license acknowledgement:

```bash
python -m benchmarks.polynorm --accept-license
```

After downloading, offline and focused runs are available:

```bash
python -m benchmarks.polynorm --offline
python -m benchmarks.polynorm --offline --locale en-US --category Date
python -m benchmarks.polynorm --offline --case en-US:1
python -m benchmarks.polynorm --offline --show-failures all
```

The overlap files are not assumed to have equal lengths; the evaluator derives
the case count from the cached JSONL files. Reports therefore distinguish raw
metrics, canonicalized category metrics, ownership-aware metrics, and a local
reviewed subset that excludes annotations in a separate quarantine file. The
upstream category and ground-truth text are never rewritten.

Cached JSONL data and the upstream license live under
`.cache/polynorm-bench/<commit>/`. Reports live under
`benchmark-results/polynorm/<run-id>/`; only metrics and metadata are intended
for summary consumption, while text-bearing failure reports are local. The
benchmark records dataset/source/dependency environment fingerprints, literal
exactness, punctuation-aware speech exactness, word error rate, unchanged cases,
exceptions, residual source-symbol counts, and locale/category/ownership
aggregates. It continues after mismatches and individual runtime exceptions and
does not add a score threshold to normal CI.
