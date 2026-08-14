# Google TN benchmark

Spokenform's Google TN benchmark consumes the Google text-normalization TSV
format also used by NVIDIA NeMo. It is called **Google TN** because the format
belongs to the Google text-normalization corpus; NeMo is one consumer, not a
runtime dependency or a separate corpus format.

This is an offline diagnostic benchmark. Google TN targets were produced by an
existing normalization system and are not unconditional human gold truth. Raw
and reviewed metrics should be inspected alongside PolyNorm, Proteno, mapping,
identity-safety, protected-literal, and unit-test results. It is not a normal
CI or release gate.

## Local data

Supply a local English `en_with_types` directory. The default `test` split uses
the official evaluation shard `output-00099-of-00100` and its first 100002
physical lines:

```bash
python -m benchmarks.google_tn \
  --data-dir /path/to/en_with_types
```

Useful focused runs are:

```bash
python -m benchmarks.google_tn \
  --data-dir /path/to/en_with_types --class DATE --limit 500

python -m benchmarks.google_tn \
  --data-dir /path/to/en_with_types --case en:099:000123 \
  --split test-full --show-failures all
```

`test-full` reads the complete evaluation shard; `all` reads all local output
shards. `--limit`, class filters, and case filters do not renumber source-derived
case IDs. The initial implementation deliberately does not download data or
claim a corpus license: callers provide and manage their local source files.

## Format and integrity

Rows are `CLASS<TAB>WRITTEN<TAB>SPOKEN`, and `<eos>\t<eos>` ends a sentence.
`<self>`, `sil`, and compatibility `<sil>` project to the written field for
forward text normalization. Unknown classes remain visible. Source sentences
are assembled by joining written fields with one ASCII space (`field_join_v1`),
which makes every row span exact and reproducible without a detokenizer.

The benchmark records source filename, byte size, SHA256, selected line range,
surface and sentinel policies, Spokenform/dependency versions, Python/platform,
and benchmark configuration. Gold class labels are grouping metadata only and
are never passed as annotations or semantic hints to `spokenform.prepare()`.

## Profiles and metrics

The default profile uses `en_US`, `use_spacy=False`, `symbol_mode="none"`,
conservative acronym and literal policies, and `long_number_mode=preserve`.
`--profile extended`, `--normalize-literals`, and the explicit
`--long-number-mode cardinal` option are experiments, not default behavior.

Reports include sentence literal/speech/equivalent exactness, presentation-only
differences, semantic failures, WER, unchanged cases, normalization versus
identity rates, mapped row/span exactness, ambiguity counts, and raw-class
aggregates. Row outcomes distinguish `correct-transform`, `identity-preserved`,
`transform-miss`, `wrong-transform`, `identity-mutation`, `presentation-only`,
`mapping-ambiguous`, and `runtime-error`.

Each run is written under `benchmark-results/google-tn/<run-id>/` with
`summary.json`, source-bearing `rows.jsonl` and `failures.jsonl`, and grouped
Markdown failure reports. Keep these results local. Compare runs with:

```bash
python -m benchmarks.google_tn_compare \
  benchmark-results/google-tn/<before> \
  benchmark-results/google-tn/<after>
```

The comparison reports aggregate, raw-class, outcome, resolved, new, and
remaining stable-ID deltas.

## Scope boundaries

The parser is language-neutral, but the official adapter initially supports
English to `en_US` only. This feature adds no NeMo, PyTorch, Transformers,
Moses, Kaggle, neural, WFST, or network dependency. It does not add global
NeMo character rewrites, oracle class input, Russian/Polish runtime support, or
an automatic digitwise long-number default.
