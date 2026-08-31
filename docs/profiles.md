# Speech profiles

`SpeechProfile` is the Python API for a reusable, domain-specific abbreviation glossary.
It is separate from `PreparationConfig`: configuration controls pipeline policy, while a
profile supplies user-owned speech data.

## Basic usage

```python
from spokenform import GlossaryEntry, SpeechProfile, prepare

profile = SpeechProfile(
    name="operations",
    language="en",
    glossary=(
        GlossaryEntry("AAR", "after-action review"),
        GlossaryEntry("AO", "area of operations", read_as="letters"),
        GlossaryEntry(
            "AAA",
            "anti-aircraft artillery",
            read_as="custom",
            spoken_form="Triple A",
        ),
    ),
)

result = prepare("AAA enters the AO after the AAR.", profile=profile)
assert result.spoken_text == (
    "Triple A enters the A O after the after-action review."
)
```

The supported `read_as` values are:

- `long_form`, the default, expands to `long_form`.
- `letters`, spells the matched source surface, such as `AO` to `A O`.
- `custom`, uses the required non-empty `spoken_form`.

The dependency performs matching, aliases, regular-expression guards, POS guards,
case sensitivity, sentence case, and exact source replacement generation. For example:

```python
GlossaryEntry(
    abbreviation="AAR",
    long_form="after-action review",
    aliases=("A.A.R.",),
    case_sensitive=True,
    only_if_followed_by=r"^\s+complete$",
)
```

`SpeechProfile` and `GlossaryEntry` are frozen and hashable. Abbreviations and aliases
must be clean, non-empty strings. A profile rejects duplicate canonical or alias surfaces
using case-folded comparison, so ambiguous imported glossaries fail before compilation.
Invalid guard expressions also fail during construction.

## Isolation and precedence

A profile is compiled into one cached isolated `abbr2words.Expander`. Reusing the same
frozen profile does not rebuild its registry for every call. Profile calls contain the
bundled registry plus that profile's entries, but do not inherit process-global entries
created with `add_abbreviation()`.

When no profile is supplied, `prepare()` continues to use the existing shared registry.
This preserves the compatibility behavior of `add_abbreviation()`. When a profile is
supplied, an explicit profile entry overrides a bundled abbreviation. Two profiles can
therefore assign different meanings to the same surface without affecting one another.

For a profile-owned surface, `GlossaryEntry.read_as` determines the result. For unrelated
registered entries, `PreparationConfig.registered_acronym_mode` remains in control. For
unknown uppercase terms, `generic_acronym_mode` and `generic_acronym_case` remain in
control. A profile entry using `read_as="letters"` automatically enables the dependency's
registered source-spelling policy, without changing semantic long-form entries.

Structured semantic replacements and caller-protected spans continue to outrank profile
abbreviations. Profile replacements use the normal Spokenform abbreviation stage, so
`PreparedText.source_replacements`, mapped edits, and offset maps retain their existing
source coordinates and provenance.

`prepare_for_kokorog2p()` accepts the same optional `profile` argument and forwards it to
`prepare()`.

## Current boundaries

The v1 profile API intentionally has no JSON or YAML format, CLI profile loader, profile
inheritance or merging, automatic ambiguity resolution, military time policy, SSML, or
phoneme override support. These can be added after runtime profile semantics are stable.

Spokenform requires `abbr2words>=0.2.13,<0.3.0` for the isolated expander, bulk
registration, speech strategies, custom spoken forms, and exact replacement APIs used by
profiles.
