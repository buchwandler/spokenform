# Protected text

Automatic protection covers URLs, email addresses, and semantic-version-like
strings. Caller-defined spans can protect additional source ranges.

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
