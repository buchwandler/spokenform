# Benchmarks

The benchmark suites are diagnostic and release-supporting tools, not a
replacement for the semantic regression and false-positive tests.

```{toctree}
:maxdepth: 1

polynorm
proteno
google_tn
```

The benchmark ownership and release policy are documented in
[`benchmarks/OWNERSHIP.md`](../benchmarks/OWNERSHIP.md). PolyNorm and Proteno
measure specialized diagnostic behavior and failure reductions; Google TN is
an offline English text-normalization comparison. Their data and reports live
under `benchmarks/` and should be interpreted with the safety and quarantine
guidance in the ownership document.
