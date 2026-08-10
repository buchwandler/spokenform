# PolyNorm diagnostic benchmark

Spokenform's PolyNorm adapter evaluates the overlap between the external
Apple PolyNorm-Bench corpus and the seven base languages supported by
Spokenform. The overlap is `de-DE`, `en-US`, `es-MX`, `fr-FR`, and `it-IT`;
the default run therefore evaluates 5 × 540 = 2700 cases. PolyNorm BCP-47
tags are translated only inside the benchmark adapter (`en-US` becomes
Spokenform `en`); they are not a Spokenform API convention.

The source is pinned to commit
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

Cached JSONL data and the upstream license live under
`.cache/polynorm-bench/<commit>/`. Reports live under
`benchmark-results/polynorm/<run-id>/`; only metrics and metadata are intended
for summary consumption, while text-bearing failure reports are local. The
benchmark records literal exactness, punctuation-aware speech exactness, word
error rate, unchanged cases, exceptions, and locale/category aggregates. It
continues after mismatches and individual runtime exceptions and does not add a
score threshold to normal CI.
