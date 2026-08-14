# Benchmark baseline — Brief 02

This is the fresh baseline for the ten-step robustness work. It was generated
from the current checkout on 2026-08-14 with the pinned local caches, before
any changes for this brief. The result directories are intentionally ignored
because their JSONL/Markdown files contain benchmark source text; the run
identity below is the durable checkpoint.

| Benchmark | Profile | Cases | Semantic failures | Identity mutations | Run |
| --- | --- | ---: | ---: | ---: | --- |
| Proteno | default | 29,348 | 5,968 | 0 | `20260814T074449Z` |
| Proteno | extended | 29,348 | 5,938 | 0 | `20260814T074731Z` |
| PolyNorm | default | 2,680 | 1,086 | n/a | `20260814T074745Z` |
| PolyNorm | extended | 2,680 | 1,056 | n/a | `20260814T074756Z` |

## Identity

- Spokenform source commit: `a93bfb96e7ee8c3cb70dd26a295daeb98dfb50ff`
- Spokenform version: `0.2.5.dev5+g672bfe544`
- `abbr2words`: `0.2.8`
- `num2words`: `0.5.14`
- Python: `3.14.6`
- Platform: `Android-16-aarch64-64bit-ELF`
- Proteno dataset commit: `8839501abaf50eeccbe21a2397cefa118eae9660`
- PolyNorm dataset commit: `f3c67e047bea6b7c40bc2466c0fdaad51d8ce67d`

Default uses `normalize_literals=False`, `generic_acronym_mode=known_only`,
registered expansion, and `long_number_mode=preserve`. This baseline predates
the ten implementation commits; later compatible runs must record their own
identity and configuration hash rather than being compared to these rows as if
they were same-configuration results.

## Stale supplied rows

The supplied failure reports are not treated as current defects until they are
reproduced under this identity. Existing regression coverage already resolves
the reported examples for contextual years (`in 1858`, `since 1972`, `until
1994`), `Late 1830s`, spaced Spanish ISBN labels, and typed versions such as
`Python 3.9.7` and `GTK+ 2.18.2.30`. Those rows remain useful as regression
fixtures, but are excluded from new-rule selection unless a fresh compatible
run reproduces them.

The remaining failure totals are diagnostic only. Ownership and safety gates are
implemented in the follow-up commits, so protected, downstream, unsupported,
extended, and owned families are no longer conflated in new reports.
