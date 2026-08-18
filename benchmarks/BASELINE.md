# Benchmark checkpoint — Brief 02

This is the fresh post-implementation rerun for the terminal-cardinal,
Spanish generated-start casing, and benchmark risk-tier reporting work. It was
generated on 2026-08-18 from the current checkout with the pinned offline
caches. The result directories remain ignored because their JSONL/Markdown
reports contain benchmark source text; the run ids and summary metrics below
are the durable checkpoint.

| Benchmark | Profile  |  Cases | Semantic failures | Presentation-only | Safety mutations | Run                |
| --------- | -------- | -----: | ----------------: | ----------------: | ---------------: | ------------------ |
| Proteno   | default  | 29,348 |             5,799 |                25 |                0 | `20260818T081825Z` |
| Proteno   | extended | 29,348 |             5,543 |                25 |                0 | `20260818T082016Z` |
| PolyNorm  | default  |  2,680 |             1,021 |                14 |                0 | `20260818T081636Z` |
| PolyNorm  | extended |  2,680 |               975 |                14 |                0 | `20260818T081641Z` |

## Identity

- Spokenform source commit: `e6cc5d34392d606434f95853691f3c1d611331c2`
- Spokenform version: `0.2.6`
- `abbr2words`: `0.2.9`
- `num2words`: `0.5.14`
- Python: `3.13.14`
- Platform: `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.42`
- Proteno dataset commit: `8839501abaf50eeccbe21a2397cefa118eae9660`
- PolyNorm dataset commit: `f3c67e047bea6b7c40bc2466c0fdaad51d8ce67d`

Per-run `summary.json` files also record the locale mapping and configuration
hash used for comparison safety:

| Run                         | Profile  | Config hash                                                        |
| --------------------------- | -------- | ------------------------------------------------------------------ |
| PolyNorm `20260818T081636Z` | default  | `8dfdd642beb7c3ea884135768608839351e3cac72d51b55cd2fb117d04a739f8` |
| PolyNorm `20260818T081641Z` | extended | `2d8328416caffdc54712035b43db12652b6d0ac9697fe7f7e4fc7b73da03976d` |
| Proteno `20260818T081825Z`  | default  | `d3cbb2272802124e4d2e7fb305840fa57ce7c504247e8b1ba2dc22ca4f28f511` |
| Proteno `20260818T082016Z`  | extended | `75a79e16d971c00732288bf399b35e761341ee6b2abf39efcedad41eea1b444a` |

## Categorized failure summary

The refreshed reports now store per-row ownership, failure phase, and risk-tier
diagnostics. Key rollups from the fresh summaries:

| Run               | High risk | Medium risk | Low risk | Unrecognized | Structured rendering | Dependency-abbr2words |
| ----------------- | --------: | ----------: | -------: | -----------: | -------------------: | --------------------: |
| PolyNorm default  |       629 |         260 |      402 |          468 |                  779 |                    67 |
| PolyNorm extended |       590 |         257 |      401 |          353 |                  850 |                    66 |
| Proteno default   |     3,863 |       3,073 |    7,218 |        2,868 |                9,392 |                 1,060 |
| Proteno extended  |     3,342 |       2,881 |    7,206 |        2,665 |                9,188 |                   742 |

Compared with the 2026-08-14 checkpoint, semantic failures dropped in all four
runs and the safety-mutation gates remained at zero.
