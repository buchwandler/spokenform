"""Protect caller-selected text while normalizing the rest."""

from spokenform import ProtectedSpan, prepare

source = "Keep Dr. unchanged, but speak 12 and preserve https://example.org/v2."
literal = ProtectedSpan(source.index("Dr."), source.index("Dr.") + len("Dr."))

prepared = prepare(
    source,
    language="en",
    protected_spans=[literal],
)

print(prepared.spoken_text)
print(prepared.warnings)
