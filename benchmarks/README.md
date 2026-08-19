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
`--profile default|extended`, `--normalize-literals`, `--show-failures all`,
and `--report html|none`.
Reports are written to
`benchmark-results/polynorm/<run-id>/`. `summary.json` contains metrics and
metadata only; the JSONL and Markdown failure reports contain source text and
remain local. `report.html` is a self-contained dashboard covering KPI,
locale/category breakdowns, diagnostics, failures, metadata, and optional
oracle views.

The default profile calls `prepare(..., normalize_literals=False)` and treats
URL/email/version rows as protected ownership. The extended profile calls
`normalize_literals=True` and measures optional literal verbalization. Keep
the profile field when comparing reports.

PolyNorm is a discovery tool, not a normal CI or release gate. The benchmark
does not make unsupported PolyNorm locales part of Spokenform's public API.

Fresh runs record the resolved Spokenform, `abbr2words`, and `num2words`
versions, source and dataset commits, locale mapping, profile, and a stable
configuration hash. Each report also contains a machine-readable `identity`
block plus per-row ownership, phase, and risk-tier diagnostics so semantic
follow-up can stay separated from presentation-only differences. The pinned
snapshot currently contains 2,680 overlap cases; reports use the available
count rather than assuming every locale has the same number of rows.

## Fresh comparison workflow

Use the same pinned inputs and profile for every comparison:

```text
baseline -> patch -> rerun same profile -> compare -> inspect new failures
```

`benchmarks.proteno_compare` and `benchmarks.polynorm_compare` refuse to
compare runs with different dataset commits, locale mappings, profiles, or
critical configuration hashes. For an intentional cross-profile experiment,
pass `--allow-incompatible`; the resulting JSON records the mismatch and the
override explicitly. Do not compare an old failure Markdown file manually
against a new checkout.

Release-facing metrics are split into `safety/default`, `owned`, `extended`,
`protected`, `downstream`, `unsupported`, and `quarantine`. Raw failure-count
reductions in protected or unsupported families do not replace the identity
and new-failure gates.

The full ownership table, profile contract, quarantine policy, and residual
non-goals are in [OWNERSHIP.md](OWNERSHIP.md).

See the detailed [PolyNorm documentation](../docs/polynorm.md).

## Proteno benchmark

`python -m benchmarks.proteno --accept-license` runs the pinned English and
Spanish Proteno diagnostic benchmark. Data is cached under
`.cache/proteno/<commit>/`; reports are written under
`benchmark-results/proteno/<run-id>/`. Use `--profile extended`,
`--normalize-literals`, or `--report none` for the opt-in literal profile and
HTML toggle. `report.html` is a self-contained dashboard covering KPI,
language/case-kind views, diagnostics, failures, metadata, and optional oracle
details. Reports keep semantic, presentation-only, ownership, and risk-tier
diagnostics separate. The external data is never packaged or committed. See the detailed
[Proteno documentation](../docs/proteno.md).

## Google TN benchmark

`python -m benchmarks.google_tn --data-dir /path/to/en_with_types` runs the
offline English Google TN / NeMo-compatible TSV diagnostic benchmark. The
default uses the official `output-00099-of-00100` evaluation shard and first
100002 physical lines, maps English to `en_US`, and does not download or vendor
the corpus. Use `--split test-full|all`, `--class`, `--case`, `--limit`,
`--profile extended`, and explicit `--long-number-mode` options for focused
experiments.

The benchmark preserves upstream semiotic classes as evaluation metadata only;
it never passes gold classes to `prepare()`. Reports distinguish transform
misses, wrong transforms, identity mutations, presentation-only differences,
and ambiguous mappings, and record source-file SHA256 provenance. Google TN is
a diagnostic rather than a human-gold oracle, normal CI gate, or release gate.
Source-bearing reports remain local under `benchmark-results/google-tn/`.
See the detailed [Google TN documentation](../docs/google_tn.md).

## Async Voice TTS Normalization Benchmark

`python -m benchmarks.async_tn --suite all` runs the pinned English and multilingual Async TN adapter. The source is Apache-2.0, cached under `.cache/async-tn/<commit>/`, and never vendored. Use `--suite english|multilingual`, `--language`, `--category`, `--case`, `--limit`, `--offline`, `--refresh`, `--download-only`, `--profile default|extended`, `--normalize-literals`, `--show-failures`, and `--report html|none`.

The multilingual suite supports `en`, `de`, `es`, `fr`, `it`, and `pt`; English maps to `en_US`. Each sentence is prepared once and annotated units are projected through source mappings. Ambiguous mappings and malformed source rows are quarantined rather than guessed. Results include explicit denominators, source hashes, JSONL records, Markdown failures, a static escaped HTML dashboard, and reference data from the pinned upstream category files.

The dashboard clearly separates deterministic Spokenform text metrics from published upstream audio/LLM judge scores. Its failure explorer uses authoritative sentence-level expected/actual values and treats unit projections as diagnostic-only when cross-boundary edits make them ambiguous. It does not calculate a mixed-method winner. Compare compatible runs with `python -m benchmarks.async_tn_compare before after`; incompatible dataset or configuration identities are rejected by default. See the detailed [Async TN documentation](../docs/async_tn.md).

## Spokenform Gold benchmark

`python -m benchmarks.spokenform_gold` downloads the reviewed Spokenform Gold repository at pinned commit `ba55d631a45a0fe8b3d87ad58beef2843c617151`, builds and verifies the experimental `0.1.0-exp` release, evaluates the default `test` split, and writes a self-contained HTML report. The source and materialized release are cached under `.cache/spokenform-gold/<commit>/`; cached data is not packaged with Spokenform.

Use `--offline` to reuse a populated cache, `--refresh` to repopulate it, `--download-only` to populate and verify without scoring, `--cache-dir` to choose another cache, `--gold-root /path/to/release` to use an explicit local release, `--split test|dev|all`, `--mode canonical|accepted`, and `--report html|none`. Results are written under `benchmark-results/spokenform-gold/<run-id>/` with `summary.json`, `predictions.jsonl`, `rows.jsonl`, `failures.jsonl`, `failures.md`, and, by default, `report.html`.

The Gold corpus remains a diagnostic benchmark rather than a stable release gate. The adapter records source provenance and uses Gold's own scoring, release verification, and materialization policy. It does not automatically hydrate restricted PolyNorm or Proteno sources.

## v0.3 policy oracle coverage

The bounded configuration lattice includes the policy expansion `sequence-fallback-spell` in addition to the conservative compatibility profiles. Its results are reported separately from normal configuration gains because spelling residual sequence-shaped text intentionally expands ownership. Targeted domain allowlist and `surface + sequence-fallback-spell` experiments remain outside the normal lattice.

Countdown Gold and release regression cases should record the canonical model-neutral boundary `three - two - one`. Semantic speech metrics may treat punctuation-free and boundary-bearing forms as equivalent, while exact presentation checks retain the Spokenform contract. Benchmark category labels remain evaluation metadata and are never passed to `prepare()`. The reviewed numeric gate remains an explicit release-readiness item until its current failure inventory is resolved or explained.
