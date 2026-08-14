# Benchmark ownership and profiles

Benchmark results are diagnostics for the written-to-spoken contract. A lower
raw failure count is not sufficient for release: identity mutations,
protected-span mutations, and new safety failures remain hard gates.

| Ownership | Meaning | Release treatment |
| --- | --- | --- |
| `safety/default` | Identity and conservative default rows | Must not regress; identity mutations stay zero on the fresh baseline |
| `owned` | High-confidence semantics owned by Spokenform | Primary correctness target |
| `extended-candidate` | Strict coordinates, legal references, formula, math, music, biology, and similar families | Reviewed separately; no broad-shape expansion |
| `protected` | URLs, e-mail addresses, versions, caller-protected spans | Must remain unchanged in the default profile |
| `downstream` | Phoneme-sensitive years, Roman numerals, phone/ID sequences, and model-owned rendering | Not a Spokenform failure unless explicitly transferred |
| `unsupported` | Outside the supported language/category contract | Reported, never silently promoted to owned |
| `quarantine` | Reproducibly malformed or questionable upstream target | Visible in raw reports, excluded from reviewed aggregates |

## Profiles

`default` is the release safety baseline: literal promotion is disabled,
unknown acronyms are untouched, registered acronyms use semantic expansion,
and long numbers are preserved.

`extended` is an opt-in speech experiment: literal promotion is enabled,
unknown acronyms use conservative protection, registered acronyms use source
letter spelling, and contextual long-number normalization may be evaluated.

An optional caller-level `aggressive` experiment can select
`generic_acronym_mode="spell_unknown"` and
`long_number_mode="cardinal"`. It is not a benchmark release profile and must
not be used to justify default safety changes.

## Comparison and quarantine policy

Compare only reports with matching dataset commits, source/dependency identity,
locale mapping, profile, and configuration hash. Cross-profile or cross-source
comparisons require an explicit compatibility override and are exploratory.
Quarantine entries are local reviewed annotations; they never rewrite upstream
data or hide raw failures.

The selected extended semantic families remain strict candidates. Coordinates
must satisfy directional ranges, legal references require a recognized grammar,
formulae require element-symbol and balanced-parenthesis shape, mathematics
requires operators, music requires context, and biology requires controlled
genus/species shape. Ordinary words and unlabeled alphanumeric strings remain
outside these families.
