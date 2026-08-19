# Candidate Oracle Baseline

Fresh oracle-enabled baselines from the current checkout. Rates are named explicitly:

```text
selection_gap_rate = selection_gap_count / eligible_semantic_failure_count
fully_recoverable_selection_gap_rate = fully_recoverable_selection_gap_count / eligible_semantic_failure_count
```

The denominator excludes dependency-owned, protected, policy, presentation-only, runtime-error,
and quarantined rows. It includes only eligible semantic failures. A selection gap means that a
better emitted candidate path exists. A fully recoverable gap additionally reaches speech
equivalence with the benchmark target.

## Overall

| Benchmark | Profile  | Semantic failures | Eligible semantic failures | Selection gaps | Selection gap rate | Fully recoverable | Fully recoverable rate | Selector regret |
| --------- | -------- | ----------------: | -------------------------: | -------------: | -----------------: | ----------------: | ---------------------: | --------------: |
| PolyNorm  | default  |               881 |                        584 |             12 |            2.0548% |                 5 |                0.8562% |          2.3000 |
| PolyNorm  | extended |               835 |                        575 |             12 |            2.0870% |                 5 |                0.8696% |          2.3000 |
| Proteno   | default  |             5,793 |                      5,106 |              7 |            0.1371% |                 1 |                0.0196% |          1.4722 |
| Proteno   | extended |             5,537 |                      4,853 |              7 |            0.1442% |                 1 |                0.0206% |          1.4722 |
| Async TN  | default  |             3,871 |                      2,622 |             62 |            2.3646% |                16 |                0.6102% |         10.1049 |

The reported selection gap count and fully recoverable count are intentionally different metrics.

## Run artifacts

- PolyNorm default: `artifacts/oracle-v2-baseline/polynorm-default/20260819T053818Z`
- PolyNorm extended: `artifacts/oracle-v2-baseline/polynorm-extended/20260819T054507Z`
- PolyNorm extended numeric gate: `artifacts/oracle-v2-baseline/polynorm-extended-numeric/20260819T054513Z`
- Proteno default: `artifacts/oracle-v2-baseline/proteno-default/20260819T054230Z`
- Proteno extended: `artifacts/oracle-v2-baseline/proteno-extended/20260819T054428Z`
- Async TN default: `artifacts/oracle-v2-baseline/async-tn/20260819T054457295038Z`

The PolyNorm numeric gate reported 502 failures among 1,878 reviewed cases. This is baseline
evidence, not a validation result for the implementation.

## Decision gate

Selection over existing candidates remains a small recovery ceiling. The largest current
selection-gap rate is Async TN at 2.3646%, and its fully recoverable rate is 0.6102%.
These measurements support prioritizing candidate generation, rejection diagnostics, and bounded
rendering or configuration alternatives before considering a learned selector.

The oracle is diagnostic-only. It does not alter runtime normalization, protected literals,
benchmark ownership, or dependency abbreviation policy.

## Recognition-policy oracle checkpoint

The bounded configuration lattice now includes `interpretation-surface` as a separately reported variant. Targeted domain ablations use one disabled domain per run for `chemistry`, `biology`, `math`, `music`, and `sports`; domain subsets are intentionally not enumerated. These measurements are diagnostic and do not tune the contextual default. The implementation test corpus records policy suppression, selected domain/evidence metadata, and surface context-invariance separately from raw speech regret.

The Phase 5 orthographic fallback decision remains deferred. Surface mode is fail-closed, and no spell-everything fallback is enabled without benchmark and downstream user evidence.
