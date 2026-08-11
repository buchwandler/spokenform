# Protected text

Automatic protection covers URLs, email addresses, and semantic-version-like
strings. Caller-defined spans can protect additional source ranges. High-
confidence literal promotion is opt-in:

```python
result = prepare("See https://example.org/a2 and v1.2.3", language="en", normalize_literals=True)
```

With `normalize_literals=True`, structured URL, e-mail, version, and contextual
Roman candidates are rendered before generic stages. Caller-defined spans are
still absolute and always win over promotion.

```python
from spokenform import ProtectedSpan, prepare

text = "Keep Dr. literal, but verbalize 12."
start = text.index("Dr.")
result = prepare(
    text,
    language="en",
    protected_spans=[ProtectedSpan(start, start + 3)],
)
```

Tuple pairs such as `(start, end)` are also accepted. Ranges use Python string
offsets and are half-open: the start is included and the end is excluded.

Invalid or overlapping caller ranges are skipped with warnings by default.
`strict=True` turns them into `ProtectionError`.

Protection is fail-closed for structured expressions: if a caller span partially
intersects a recognized numeric quantity, the complete candidate is protected so
later generic-number or abbreviation stages cannot create a hybrid rewrite. URLs,
e-mail addresses, versions, numbers, units, abbreviations, and adjacent
unprotected expressions are covered by the adapter tests.
