"""Small repeatable spokenform benchmark matrix.

Run with ``python benchmarks/benchmark.py`` from the repository root. The
numbers are diagnostic; parity and correctness remain test-gated separately.
"""

from __future__ import annotations

import time

from spokenform import TokenAnnotation, prepare_for_kokorog2p

CASES = {
    "short sentence": "Prof. hat 2 kg.",
    "1 KiB prose": " ".join(f"Wort{index}" for index in range(180)),
    "10 KiB prose": " ".join(f"Wort{index}" for index in range(1300)),
    "many numeric expressions": " ".join("2 kg 14.05.2026 18:20" for _ in range(32)),
    "many protected spans": " ".join("https://example.org/v1.2.3" for _ in range(32)),
    "many annotations": " ".join("Prof." for _ in range(32)),
}


def main() -> None:
    for name, text in CASES.items():
        annotations = None
        if name == "many annotations":
            annotations = tuple(
                TokenAnnotation(index * 6, index * 6 + 5, text="Prof.") for index in range(32)
            )
        start = time.perf_counter()
        result = prepare_for_kokorog2p(text, "de") if annotations is None else None
        if annotations is not None:
            result = prepare_for_kokorog2p(text, "de", annotations=annotations)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result is not None
        print(f"{name:28} {elapsed_ms:9.3f} ms {len(result.spoken_text):7} chars")


if __name__ == "__main__":
    main()
