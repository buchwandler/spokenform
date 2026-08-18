# Candidate Oracle Baseline

Generated from the oracle-enabled benchmark runs completed in this checkout. Google TN oracle runs were not included because no local Google TN dataset shard was available.

## Overall

| Benchmark | Profile  | Semantic failures | Eligible semantic failures | Ambiguous rows | Selection gaps | Fully recoverable | Recoverable of eligible semantic failures | Selector regret |
| --------- | -------- | ----------------: | -------------------------: | -------------: | -------------: | ----------------: | ----------------------------------------: | --------------: |
| PolyNorm  | default  |               904 |                        592 |            508 |             12 |                 5 |                                     2.03% |          2.3000 |
| PolyNorm  | extended |               858 |                        583 |            509 |             12 |                 5 |                                     2.06% |          2.3000 |
| Proteno   | default  |              2264 |                       2264 |           1961 |              2 |                 0 |                                     0.09% |          0.2883 |
| Proteno   | extended |              2150 |                       2150 |           1961 |              2 |                 0 |                                     0.09% |          0.2883 |
| Async TN  | default  |              3943 |                       2695 |            988 |             64 |                18 |                                     2.30% |         10.1049 |

Run directories:

- `PolyNorm / default` → `benchmark-results/polynorm/20260818T135306Z`
- `PolyNorm / extended` → `benchmark-results/polynorm/20260818T135313Z`
- `Proteno / default` → `benchmark-results/proteno/20260818T135403Z`
- `Proteno / extended` → `benchmark-results/proteno/20260818T135453Z`
- `Async TN / default` → `benchmark-results/async-tn/20260818T135525375538Z`
- `Google TN` → unavailable locally; no oracle run performed.

## By language

| Benchmark | Profile  | Language | Selection gaps | Fully recoverable | Selector regret |
| --------- | -------- | -------- | -------------: | ----------------: | --------------: |
| Async TN  | default  | fr       |             11 |                 8 |          4.0569 |
| Async TN  | default  | en       |             16 |                 0 |          2.1339 |
| Async TN  | default  | pt       |             11 |                 4 |          1.4749 |
| Async TN  | default  | es       |             14 |                 4 |          1.2084 |
| Async TN  | default  | it       |             10 |                 2 |          1.1372 |
| PolyNorm  | default  | it-IT    |              4 |                 3 |          0.7733 |
| PolyNorm  | extended | it-IT    |              4 |                 3 |          0.7733 |
| PolyNorm  | default  | fr-FR    |              2 |                 1 |          0.5096 |
| PolyNorm  | extended | fr-FR    |              2 |                 1 |          0.5096 |
| PolyNorm  | default  | es-MX    |              2 |                 1 |          0.4500 |
| PolyNorm  | extended | es-MX    |              2 |                 1 |          0.4500 |
| PolyNorm  | default  | de-DE    |              3 |                 0 |          0.3171 |

## By category

| Benchmark | Profile  | Category                | Selection gaps | Selector regret |
| --------- | -------- | ----------------------- | -------------: | --------------: |
| Async TN  | default  | acronym                 |             45 |          7.4808 |
| Async TN  | default  | biology                 |              4 |          1.0000 |
| PolyNorm  | default  | Currency                |              2 |          0.6250 |
| PolyNorm  | extended | Currency                |              2 |          0.6250 |
| PolyNorm  | default  | Vehicle or Product Code |              4 |          0.5304 |
| PolyNorm  | extended | Vehicle or Product Code |              4 |          0.5304 |
| Async TN  | default  | score_or_range          |              4 |          0.4583 |
| PolyNorm  | default  | Legal Reference         |              1 |          0.3846 |
| PolyNorm  | extended | Legal Reference         |              1 |          0.3846 |
| Async TN  | default  | phone                   |              3 |          0.3768 |
| Async TN  | default  | currency                |              3 |          0.3698 |
| PolyNorm  | default  | Time                    |              1 |          0.3000 |

## By primary rule conflict

| Benchmark | Profile  | Conflict                                    | Cases | Selector regret |
| --------- | -------- | ------------------------------------------- | ----: | --------------: |
| Async TN  | default  | `sequence.isbn -> sequence.phone`           |    18 |          4.7699 |
| Async TN  | default  | `en.quantity -> sequence.mac`               |     8 |          1.6247 |
| Async TN  | default  | `sequence.phone -> sequence.iban`           |    20 |          1.0862 |
| Async TN  | default  | `sequence.biomedical -> sequence.product`   |     6 |          1.0000 |
| PolyNorm  | default  | `sequence.biomedical -> sequence.product`   |     3 |          0.5357 |
| PolyNorm  | extended | `sequence.biomedical -> sequence.product`   |     3 |          0.5357 |
| PolyNorm  | default  | `sequence.vin -> sequence.product`          |     4 |          0.5304 |
| PolyNorm  | extended | `sequence.vin -> sequence.product`          |     4 |          0.5304 |
| Async TN  | default  | `sequence.sports -> sequence.numeric-range` |    15 |          0.5083 |
| Async TN  | default  | `en.currency -> sequence.exchange-rate`     |     2 |          0.5000 |
| Async TN  | default  | `it.time -> it.currency`                    |     4 |          0.4467 |
| Async TN  | default  | `it.currency -> sequence.exchange-rate`     |     1 |          0.3846 |

## Oracle limitations

| Benchmark | Profile  | Truncated rows | Runtime-error rows | Policy exclusions | Dependency exclusions | Unicode exclusions | Other unscorable reasons |
| --------- | -------- | -------------: | -----------------: | ----------------: | --------------------: | -----------------: | -----------------------: |
| PolyNorm  | default  |              0 |                  0 |               405 |                   198 |                  0 |                        0 |
| PolyNorm  | extended |              0 |                  0 |               405 |                   198 |                  0 |                        0 |
| Proteno   | default  |              1 |                  0 |                 0 |                     0 |                  0 |                        0 |
| Proteno   | extended |              1 |                  0 |                 0 |                     0 |                  0 |                        0 |
| Async TN  | default  |              3 |                109 |              1089 |                   533 |                  0 |                        0 |

Observations:

- No Unicode-stage exclusions were observed in the completed PolyNorm, Proteno, or Async TN runs.
- Proteno truncated exactly one Spanish row in both profiles; Async TN truncated three rows and isolated 109 runtime-error rows without aborting the run.
- The oracle is diagnostic-only; it did not change runtime benchmark behavior, protection rules, or ownership policy.

## Decision gate

- **PolyNorm:** ~2.0% of eligible semantic failures were recoverable through existing candidate selection alone in both profiles (12 / 592 default, 12 / 583 extended).
- **Proteno:** selector headroom was negligible at ~0.09% in both profiles (2 recoverable eligible semantic failures each).
- **Async TN:** the strongest signal was still only ~2.3% recoverable eligible semantic failures (62 / 2695), concentrated in acronym/identifier-style conflicts such as `sequence.isbn -> sequence.phone`, `en.quantity -> sequence.mac`, and `sequence.phone -> sequence.iban`.
- **Google TN:** no local dataset shard was available, so this report does not add sentence-level Google TN selector evidence.

**Recommendation:** do **not** start a selector experiment yet. The best observed recoverable rate is well below the brief's suggested double-digit threshold for meaningful selection headroom. The next implementation cycle should prioritize candidate-generation or rendering improvements, especially the high-regret Async TN acronym/identifier families and the small set of PolyNorm product/currency/legal conflicts surfaced above.
