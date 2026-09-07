# Spokenform implementation brief: support the full `num2words` / `abbr2words` language contract

## Status

Implementation brief based on reconstructed snapshots of the attached `spokenform` and `abbr2words` repositories.

The target is **language coverage parity without false feature parity**. Spokenform should accept and safely process every language family and explicit locale overlay exposed by the current `abbr2words` registry, while preserving the existing reviewed structured behavior for the languages that already have it.

The central architectural rule is:

> A language being supported by Spokenform must not imply that every Spokenform semantic recognizer is reviewed for that language.

The current code conflates those concepts. This brief separates them.

---

## 1. Goal

Make `spokenform` support the same language universe as the attached `abbr2words` registry / pinned current-master `num2words` contract.

### 49 base keys

`am`, `ar`, `az`, `be`, `bn`, `ca`, `ce`, `cs`, `cy`, `da`, `de`, `en`, `eo`, `es`, `fa`, `fi`, `fr`, `he`, `hi`, `hu`, `hy`, `id`, `is`, `it`, `ja`, `kn`, `ko`, `kz`, `lt`, `lv`, `mn`, `nl`, `no`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `sr`, `sv`, `te`, `tet`, `tg`, `th`, `tr`, `uk`, `vi`, `zh`.

### 17 explicit locale overlays

`en_GB`, `en_IN`, `en_NG`, `en_US`, `es_CO`, `es_CR`, `es_GT`, `es_MX`, `es_NI`, `es_VE`, `fr_BE`, `fr_CH`, `fr_DZ`, `pt_BR`, `zh_CN`, `zh_HK`, `zh_TW`.

Total dependency registry contract: **66 keys**.

Resolution must:

- trim input;
- accept `-` and `_`;
- normalize base language to lower case and region to upper case;
- try an exact registered locale first;
- then fall back to its registered base;
- keep `eo` and `es_NI`;
- reject `eu`;
- preserve existing Spokenform compatibility aliases where intentional.

Required examples:

```python
normalize_language(" pt-BR ") == "pt_BR"
normalize_language("fr_FR") == "fr"
normalize_language("en-gb") == "en_GB"
normalize_language("es-ni") == "es_NI"

normalize_language("EU")  # raises ValueError
```

---

## 2. Executive recommendation

Do **not** implement this by merely replacing the current 17-language tuple with 49 languages.

Today `SUPPORTED_BASE_LANGUAGES` implicitly means several different things in different areas:

1. globally accepted Spokenform languages;
2. KokoroG2P integration-profile languages;
3. languages with a `spokenform.locales.<lang>` implementation;
4. languages with explicit sequence digit/punctuation vocabularies;
5. languages with reviewed numeric decimal/grouping semantics.

These sets are not equivalent.

The correct migration is:

1. introduce one global language registry;
2. split global support from specialist capability sets;
3. route exact `abbr2words` locale overlays correctly;
4. make generic number support backend/capability-driven;
5. make unreviewed numeric punctuation and structured semantics fail closed;
6. keep the existing KokoroG2P language profile independent;
7. add generated registry-parity tests and a generated documentation matrix.

This provides useful support for all target keys without introducing English leakage or pretending that every language has the same semantic maturity.

---

## 3. Current architecture findings

### 3.1 Global language support is currently owned by the KokoroG2P profile

Current `spokenform/language.py` contains the equivalent of:

```python
_KOKOROG2P_PROFILES = frozenset({...17 languages...})
SUPPORTED_BASE_LANGUAGES = tuple(sorted(_KOKOROG2P_PROFILES))
```

This is the main architectural issue.

A downstream TTS integration profile should be a **consumer capability** of Spokenform. It should not define which languages Spokenform itself accepts.

The current 17 families are:

`ar`, `cs`, `de`, `en`, `es`, `fr`, `he`, `it`, `ja`, `kk`, `ko`, `pt`, `ru`, `sv`, `th`, `vi`, `zh`.

Compared with the target dependency contract, the currently missing families are:

`am`, `az`, `be`, `bn`, `ca`, `ce`, `cy`, `da`, `eo`, `fa`, `fi`, `hi`, `hu`, `hy`, `id`, `is`, `kn`, `lt`, `lv`, `mn`, `nl`, `no`, `pl`, `ro`, `sk`, `sl`, `sr`, `te`, `tet`, `tg`, `tr`, `uk`.

That is **32 additional base families**.

Kazakh is a naming exception: current Spokenform exposes `kk`, while both attached semantic dependencies use `kz`. This should be handled deliberately at the dependency boundary rather than letting it infect every registry.

### 3.2 `resolve_abbr2words_language()` currently discards most exact locale overlays

Current `spokenform/language.py` includes:

```python
_EXACT_ABBR2WORDS_LOCALES = frozenset({"es_MX", "zh_CN"})
```

and collapses other regional forms to their base before calling `abbr2words`.

That is no longer consistent with the attached `abbr2words` registry, which has all 17 explicit overlays.

Information currently lost includes:

- `en_GB`
- `en_IN`
- `en_NG`
- `en_US`
- `es_CO`
- `es_CR`
- `es_GT`
- `es_NI`
- `es_VE`
- `fr_BE`
- `fr_CH`
- `fr_DZ`
- `pt_BR`
- `zh_HK`
- `zh_TW`

Fix this early. It is low risk and immediately improves dependency parity.

### 3.3 Stable and current-master `num2words` support are intentionally different

The attached `abbr2words/tests/data/num2words_language_registry.json` pins:

- stable `num2words` contract: `v0.5.14`;
- a current-master commit;
- 45 stable base keys;
- 49 current-master base keys.

The master-only base languages in that attached contract are:

- `hi`
- `hy`
- `mn`
- `zh`

Spokenform already handles Chinese numerals separately with `cn2an`.

Therefore the practical released-number-backend gap is initially:

- `hi`
- `hy`
- `mn`

All three should still be valid **Spokenform language keys**, because `abbr2words` supports them. Numeric capability needs to be represented independently.

Do not add a Git dependency on unreleased `num2words` master to the normal installation just to make the registry count match.

### 3.4 Generic plain-number support is unnecessarily blocked by the 17-language tuple

`spokenform/numbers.py` imports `SUPPORTED_BASE_LANGUAGES`.

Its private `_base_language()` rejects anything outside that set.

`normalize_plain_numbers()` calls that helper.

Consequently, many languages already supported by installed `num2words` cannot currently use the normal Spokenform number stage.

Examples include Dutch, Polish, Turkish, Ukrainian and many others.

This restriction must be replaced by a numeric-backend capability check.

### 3.5 Numeric defaults contain unsafe English fallback behavior

`spokenform/numeric_lexeme.py` currently has generic fallbacks equivalent to:

```python
NumericSpeechPolicy("point", "digitwise")
NumericPunctuationPolicy(".", (",", " "))
```

for languages without an explicit policy.

Once the global registry grows, this is unsafe.

An unreviewed language must not silently inherit:

- English decimal word `point`;
- dot-decimal semantics;
- comma-grouping semantics.

For a newly admitted language without reviewed numeric punctuation:

- separator-free integer cardinal conversion can be enabled when a backend exists;
- punctuation-bearing numeric lexemes should remain unchanged unless an explicit reviewed policy exists.

### 3.6 Shared sequence rendering is not universal

`spokenform/sequences.py` has explicit digit names, letter names and punctuation vocabulary only for the current small language set.

Its language helper raises when a language lacks an explicit digit policy.

Several tests currently parameterize `SUPPORTED_BASE_LANGUAGES` and therefore assume:

> every supported language has explicit sequence rendering.

That assumption must move to a dedicated sequence-capability set.

### 3.7 Shared structured recognizers contain language-specific and English-default rendering

`spokenform/recognizers/sequences.py` contains several constructs conceptually similar to:

```python
mapping.get(base_language(language), "english fallback")
mapping.get(base_language(language), mapping["en"])
```

These are only safe when the recognizer is explicitly restricted to languages with reviewed output.

They become dangerous when 49 base languages are admitted globally.

A new baseline language must not emit English words such as:

- `point`;
- `to`;
- `quarter`;
- `version`;
- `squared`;
- English currency names;
- English punctuation names;

merely because a lookup table has no local entry.

### 3.8 Structured locale dispatch is currently a 17-language explicit chain

`spokenform/structured.py::_iter_locale_replacements()` has explicit imports for the current locale families and returns no locale replacements for everything else.

That fail-closed behavior is useful.

Do **not** create 32 empty `spokenform/locales/*.py` files simply to make registry membership appear uniform.

Locale modules should represent reviewed structured semantics, not basic registry membership.

### 3.9 Tests use the global support tuple for narrower capability assumptions

Examples include:

- `tests/test_cjk_architecture.py`
- `tests/test_sequences.py`
- `tests/test_sequence_fallback.py`
- `tests/test_kokorog2p_profiles.py`

Some of these currently assert that every global supported language has:

- a number policy;
- a numeric punctuation policy;
- a numeric speech policy;
- sequence vocabulary;
- an importable locale module;
- a Kokoro integration profile.

Those are capability tests, not global-language tests.

They must be split before increasing the registry.

---

## 4. Target support model

Use orthogonal capability sets rather than one overloaded language list.

Recommended internal concepts:

```python
SUPPORTED_BASE_LANGUAGES
SUPPORTED_LOCALES
SUPPORTED_LANGUAGE_KEYS

REVIEWED_STRUCTURED_LANGUAGES
CONSERVATIVE_INTEGRATION_LANGUAGES
SEQUENCE_POLICY_LANGUAGES
REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES
KOKOROG2P_PROFILE_LANGUAGES
```

Do not derive the narrower sets from `SUPPORTED_BASE_LANGUAGES`.

### 4.1 Global support

A globally supported language means:

- the identifier resolves deterministically;
- `prepare()` accepts it;
- Unicode/protection/whitespace stages work;
- `abbr2words` can be routed correctly;
- unsupported semantic stages preserve source rather than guessing;
- the pipeline does not crash merely because a specialist grammar is absent.

That is the minimum contract for every supported key.

### 4.2 Foundation numeric support

A language has foundation numeric support when a released backend can render ordinary cardinals.

Initially this is:

- every installed/released `num2words` converter;
- Chinese through `cn2an`.

For `hi`, `hy`, and `mn` under the pinned stable dependency contract:

- keep them as supported Spokenform languages;
- keep abbreviation handling available;
- preserve numeric source in normal `prepare()`;
- optionally attach one warning to `PreparedText.warnings`;
- do not crash.

Suggested warning:

```text
[NUMBERS] no released numeric backend for language 'hi'; numeric text preserved
```

### 4.3 Reviewed numeric punctuation support

This is separate from ordinary cardinal support.

A language with no reviewed decimal/grouping policy may safely support:

```text
2 -> localized cardinal
```

while preserving ambiguous forms such as:

```text
1.234
1,234
.5
```

until the punctuation rules are explicit.

### 4.4 Reviewed structured support

Keep the current reviewed locale families as an explicit capability set.

A reasonable initial set, based on the current implementation and tests, is:

```python
REVIEWED_STRUCTURED_LANGUAGES = frozenset(
    {
        "cs",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "ja",
        "ko",
        "pt",
        "ru",
        "sv",
        "th",
        "vi",
        "zh",
    }
)
```

Arabic, Hebrew and Kazakh currently have intentionally conservative integration modules and should remain separately classified.

Do not mark the 32 newly admitted families as reviewed structured languages.

### 4.5 KokoroG2P support

Keep the current KokoroG2P set independent:

```python
KOKOROG2P_PROFILE_LANGUAGES = frozenset(...)
```

`supports_profile()` should consult this set, not global Spokenform support.

The existing 17-language Kokoro contract can remain unchanged while Spokenform itself grows to the full dependency language universe.

---

## 5. Recommended language-registry design

### 5.1 Avoid reimplementing the entire `abbr2words` registry

`abbr2words` is already a required dependency and already owns:

- canonical registry keys;
- exact-locale resolution;
- base fallback;
- supported-language discovery;
- compatibility aliases.

Spokenform should not maintain another hand-copied list of 66 dependency keys as runtime truth unless it deliberately wants a frozen compatibility contract.

Prefer the public `abbr2words` registry API at runtime, while pinning the expected contract in Spokenform tests.

Conceptually:

```python
from abbr2words import (
    base_language as abbr2words_base_language,
    normalize_language as normalize_abbr2words_language,
    supported_languages as abbr2words_supported_languages,
)
```

### 5.2 Add a Spokenform capability descriptor

Recommended new module:

```text
spokenform/language_support.py
```

or keep it in `spokenform/language.py` if the module remains manageable.

Suggested shape:

```python
from dataclasses import dataclass
from enum import Enum


class SupportTier(str, Enum):
    FOUNDATION = "foundation"
    REVIEWED_STRUCTURED = "reviewed_structured"
    CONSERVATIVE_INTEGRATION = "conservative_integration"


@dataclass(frozen=True, slots=True)
class LanguageSupport:
    language: str
    base: str
    abbreviation_language: str
    number_backend: str | None
    number_language: str | None
    tier: SupportTier
    exact_locale: bool
    plain_cardinals: bool
    decimal_policy: bool
    structured: bool
    sequence_policy: bool
    kokorog2p_profile: bool
```

Do not use the tier alone for runtime decisions. The boolean capabilities are the meaningful contract.

The tier is mainly useful for documentation and human inspection.

### 5.3 Public discovery API

Recommended:

```python
def supported_languages(*, include_locales: bool = False) -> tuple[str, ...]:
    ...

def supports_language(language: str) -> bool:
    ...

def language_support(language: str) -> LanguageSupport:
    ...
```

Why `include_locales=False` by default?

Current Spokenform callers conceptually iterate language families, not explicit dependency overlays. Keeping base-only as the default avoids silently changing iteration cardinality from 17 to 66.

Expected after migration:

```python
len(supported_languages()) == 49
len(supported_languages(include_locales=True)) == 66
```

If exact API symmetry with `abbr2words` is considered more important than backward compatibility, defaulting `include_locales=True` is defensible, but it should be an explicit API decision rather than an accidental side effect.

### 5.4 Validate language once near the public API boundary

Currently `normalize_language()` mainly canonicalizes and unknown-language failures occur later in dependency-specific functions.

For the expanded public contract, language validity should be established before stages begin.

Recommended split:

```python
def canonicalize_language(language: str) -> str:
    """Normalize syntax, casing and compatibility aliases."""

def normalize_language(language: str) -> str:
    """Canonicalize and resolve against the Spokenform registry."""
```

`PreparationConfig.__post_init__()` should store a resolved supported language.

Subsequent stages can then assume language validity.

---

## 6. Kazakh: standards-oriented public key, dependency translation

The dependencies use `kz`.

Current Spokenform uses `kk`, which is the ISO 639-1 code and is already integrated with Kokoro-related code.

Recommended migration:

- keep Spokenform canonical `kk`;
- accept `kz` as a compatibility/dependency alias;
- translate `kk -> kz` only inside `resolve_num2words_language()` and `resolve_abbr2words_language()`;
- retain `spokenform/locales/kk.py`;
- retain KokoroG2P integration on `kk`.

Represent the equivalence explicitly:

```python
_DEPENDENCY_LANGUAGE_ALIASES = {
    "kk": "kz",
}
```

If strict public-key identity with `abbr2words` is a hard project requirement, the alternative is:

- canonical public `kz`;
- accept `kk`;
- translate `kz -> kk` for KokoroG2P.

That is more disruptive to existing Spokenform callers and is not the preferred migration.

Registry parity tests should treat `kk <-> kz` as an intentional key mapping rather than a missing language.

---

## 7. Fix `abbr2words` locale routing first

Delete the special-case ownership list:

```python
_EXACT_ABBR2WORDS_LOCALES = frozenset({"es_MX", "zh_CN"})
```

Do not manually decide in Spokenform which `abbr2words` overlays count as exact.

Instead:

1. canonicalize the Spokenform input;
2. translate dependency aliases such as `kk -> kz`;
3. let `abbr2words.normalize_language()` perform exact-first/base-second resolution.

Conceptually:

```python
def resolve_abbr2words_language(language: str) -> str:
    requested = canonicalize_language(language)
    dependency_input = _dependency_language(requested)
    return abbr2words_normalize_language(dependency_input)
```

Required behavior:

```python
resolve_abbr2words_language("en_GB") == "en_GB"
resolve_abbr2words_language("en-US") == "en_US"
resolve_abbr2words_language("es-NI") == "es_NI"
resolve_abbr2words_language("fr-CH") == "fr_CH"
resolve_abbr2words_language("pt-BR") == "pt_BR"
resolve_abbr2words_language("zh-HK") == "zh_HK"

resolve_abbr2words_language("fr-FR") == "fr"
```

Do not use unit-data presence as a runtime proxy for whether a registry key is valid. The attached `abbr2words` package already owns and tests that contract.

---

## 8. Number backend redesign

### 8.1 Keep backend selection separate from language support

Current behavior effectively says:

```python
def number_backend_for_language(language: str) -> str:
    return "cn2an" if base_language(language) == "zh" else "num2words"
```

This implies every non-Chinese supported language has a working `num2words` converter.

That is not true for current-master-only keys when runtime uses the stable `num2words` release.

Introduce a non-throwing capability resolver.

Suggested representation:

```python
@dataclass(frozen=True, slots=True)
class NumberBackend:
    name: Literal["num2words", "cn2an"]
    language: str


def resolve_number_backend(language: str) -> NumberBackend | None:
    ...
```

Rules:

1. `zh*` -> `cn2an`;
2. exact installed `num2words` locale -> exact converter;
3. otherwise installed base converter -> base converter;
4. otherwise -> `None`.

Capability probing should not raise.

Keep a strict helper for APIs that explicitly promise number conversion:

```python
def require_number_backend(language: str) -> NumberBackend:
    ...
```

### 8.2 Keep `resolve_num2words_language()` dependency-specific and strict

A function explicitly named `resolve_num2words_language()` should continue to fail when no `num2words` converter exists.

Examples:

```python
resolve_num2words_language("en_GB")  # exact if converter exists, else en
resolve_num2words_language("fr_FR")  # fr fallback
resolve_num2words_language("kk")     # kz
resolve_num2words_language("hi")     # raises with stable 0.5.14
```

Do not pretend that Chinese `cn2an` is a `num2words` language.

### 8.3 Make normal `prepare()` tolerant

The normal preparation pipeline should use `resolve_number_backend()`.

If no released backend exists:

- do not enable the plain-number conversion stage;
- preserve numeric source;
- add a clear warning if useful;
- continue all other stages.

This is the crucial distinction between:

- “Spokenform supports this language”
- “the installed number backend supports this language”.

### 8.4 Remove global-language gating from `numbers.py`

Current private `_base_language()` rejects anything outside the 17-language support tuple.

Remove that dependency.

The public language layer should validate registry membership; the number layer should validate numeric capability.

`normalize_plain_numbers()` must not reject `nl`, `pl`, `tr`, `uk`, etc. merely because there is no dedicated locale module.

---

## 9. Safe baseline plain numbers

### 9.1 Enable separator-free integer cardinals first

For newly supported languages with a working number backend, forms such as:

```text
0
2
12
123
```

are the safest initial capability.

This alone gives useful multilingual coverage.

### 9.2 Do not apply English punctuation defaults

Change the numeric policy APIs so “no reviewed punctuation policy” is explicit.

For example:

```python
@dataclass(frozen=True, slots=True)
class NumericPunctuationPolicy:
    decimal_separator: str | None
    grouping_separators: tuple[str, ...] = ()
```

For a foundation language with no reviewed punctuation semantics:

```python
NumericPunctuationPolicy(decimal_separator=None)
```

Then `parse_numeric_lexeme()` should:

- accept a separator-free integer;
- decline punctuation-bearing lexemes;
- preserve the source.

Likewise, `NumericSpeechPolicy` must not default `decimal_word` to English `"point"` for unknown languages.

### 9.3 Add punctuation policies deliberately

Future expansion should be based on reviewed static locale data, not runtime guessing.

If CLDR is used as a source, prefer a generated checked-in data file over a new mandatory runtime dependency such as Babel:

```text
scripts/generate_numeric_locale_data.py
spokenform/data/numeric_locales.json
```

The generated table should still have tests and review.

---

## 10. Structured recognition policy for newly supported languages

### 10.1 Do not send all non-CJK languages into shared semantic recognizers

Current `iter_structured_candidates()` is essentially:

```python
shared_candidates = (
    ()
    if base in {"ja", "ko", "zh"}
    else iter_sequence_replacements(...)
)
```

That becomes unsafe with a 49-language registry.

Change to an explicit capability gate:

```python
if base not in SHARED_SEQUENCE_RECOGNIZER_LANGUAGES:
    shared_candidates = ()
else:
    shared_candidates = iter_sequence_replacements(...)
```

Initially, include only languages that already have reviewed regression coverage.

Do not automatically add the 32 new families.

### 10.2 Preserve rather than emit English fallback semantics

Audit language lookups in `spokenform/recognizers/sequences.py`.

Unsafe:

```python
words.get(base, words["en"])
```

Preferred:

```python
language_words = words.get(base)
if language_words is None:
    return None
```

or, preferably in the first migration, gate the entire recognizer away from unsupported languages.

Fail-closed recognizer gating is easier to reason about and test than scattered per-word fallback changes.

### 10.3 Keep locale modules capability-based

Do not add empty files such as:

```text
spokenform/locales/am.py
spokenform/locales/az.py
...
```

just to mirror the registry.

Registry support belongs in the language layer.

Locale modules should signal implemented locale semantics.

---

## 11. Sequence rendering for all-language support

### 11.1 Split sequence capability from global support

Introduce:

```python
SEQUENCE_POLICY_LANGUAGES = frozenset(...)
```

Update tests that require explicit digit/punctuation realization to use this capability set rather than `SUPPORTED_BASE_LANGUAGES`.

### 11.2 Keep `SequenceFallbackMode.PRESERVE` as the default

This becomes more important with broad language coverage.

A user who does not explicitly opt into spelling must never receive guessed sequence pronunciation.

### 11.3 Make opt-in spelling degrade safely

For:

```python
sequence_fallback_mode="spell"
```

safe behavior for a baseline language is:

- use grapheme spacing where appropriate;
- use localized digit names from the number backend if available;
- use punctuation names only when explicit vocabulary exists;
- otherwise preserve the punctuation character.

Do not instantiate the current default `SequenceVocabulary()` for a new language because its defaults are English words.

A future neutral vocabulary could use `None` for all punctuation names.

---

## 12. Number policy refactor

Current `number_policy_for_language()` is documented as the initial KokoroG2P policy despite its generic name and location.

Split it.

Recommended:

```python
def default_number_policy_for_language(language: str) -> NumberPolicy:
    if language_has_reviewed_structured_numbers(language):
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if language_has_plain_number_backend(language):
        return NumberPolicy.PLAIN
    return NumberPolicy.NONE


def kokorog2p_number_policy_for_language(language: str) -> NumberPolicy:
    ...
```

Then:

```python
PreparationConfig.for_kokorog2p(...)
```

uses the Kokoro-specific policy.

Generic `prepare()` with `number_policy=None` should derive its behavior from the generic capability metadata.

This fixes the current issue where `None` effectively allows number stages to be attempted without proving the language can safely support them.

---

## 13. Locale overlays

An exact locale overlay is not automatically a new structured grammar.

For every exact overlay:

1. preserve the exact normalized key in `PreparedText.language`;
2. route exact `abbr2words` key when registered;
3. route exact `num2words` converter when installed, else its base;
4. use exact numeric punctuation policy only where explicitly defined;
5. use the existing base structured locale grammar unless Spokenform has a real regional semantic difference.

Example for `pt_BR`:

- abbreviations: exact `pt_BR`;
- number backend: exact `pt_BR` if available;
- structured grammar: base `pt`;
- punctuation policy: exact overlay only if needed.

Do not create `spokenform/locales/pt_BR.py` unless Brazilian Portuguese genuinely needs structured behavior different from base Portuguese.

Apply the same rule to all 17 overlays.

---

## 14. Target registry and initial capability tier

### Base-family parity

| Dependency key | Spokenform canonical key | Current Spokenform | Initial capability tier                   |
| -------------- | ------------------------ | -----------------: | ----------------------------------------- |
| `am`           | `am`                     |                 no | foundation                                |
| `ar`           | `ar`                     |                yes | conservative integration                  |
| `az`           | `az`                     |                 no | foundation                                |
| `be`           | `be`                     |                 no | foundation                                |
| `bn`           | `bn`                     |                 no | foundation                                |
| `ca`           | `ca`                     |                 no | foundation                                |
| `ce`           | `ce`                     |                 no | foundation                                |
| `cs`           | `cs`                     |                yes | reviewed structured                       |
| `cy`           | `cy`                     |                 no | foundation                                |
| `da`           | `da`                     |                 no | foundation                                |
| `de`           | `de`                     |                yes | reviewed structured                       |
| `en`           | `en`                     |                yes | reviewed structured                       |
| `eo`           | `eo`                     |                 no | foundation                                |
| `es`           | `es`                     |                yes | reviewed structured                       |
| `fa`           | `fa`                     |                 no | foundation                                |
| `fi`           | `fi`                     |                 no | foundation                                |
| `fr`           | `fr`                     |                yes | reviewed structured                       |
| `he`           | `he`                     |                yes | conservative integration                  |
| `hi`           | `hi`                     |                 no | foundation; stable numeric backend absent |
| `hu`           | `hu`                     |                 no | foundation                                |
| `hy`           | `hy`                     |                 no | foundation; stable numeric backend absent |
| `id`           | `id`                     |                 no | foundation                                |
| `is`           | `is`                     |                 no | foundation                                |
| `it`           | `it`                     |                yes | reviewed structured                       |
| `ja`           | `ja`                     |                yes | reviewed structured                       |
| `kn`           | `kn`                     |                 no | foundation                                |
| `ko`           | `ko`                     |                yes | reviewed structured                       |
| `kz`           | `kk`                     |        yes as `kk` | conservative integration                  |
| `lt`           | `lt`                     |                 no | foundation                                |
| `lv`           | `lv`                     |                 no | foundation                                |
| `mn`           | `mn`                     |                 no | foundation; stable numeric backend absent |
| `nl`           | `nl`                     |                 no | foundation                                |
| `no`           | `no`                     |                 no | foundation                                |
| `pl`           | `pl`                     |                 no | foundation                                |
| `pt`           | `pt`                     |                yes | reviewed structured                       |
| `ro`           | `ro`                     |                 no | foundation                                |
| `ru`           | `ru`                     |                yes | reviewed structured                       |
| `sk`           | `sk`                     |                 no | foundation                                |
| `sl`           | `sl`                     |                 no | foundation                                |
| `sr`           | `sr`                     |                 no | foundation                                |
| `sv`           | `sv`                     |                yes | reviewed structured                       |
| `te`           | `te`                     |                 no | foundation                                |
| `tet`          | `tet`                    |                 no | foundation                                |
| `tg`           | `tg`                     |                 no | foundation                                |
| `th`           | `th`                     |                yes | reviewed structured                       |
| `tr`           | `tr`                     |                 no | foundation                                |
| `uk`           | `uk`                     |                 no | foundation                                |
| `vi`           | `vi`                     |                yes | reviewed structured                       |
| `zh`           | `zh`                     |                yes | reviewed structured / `cn2an`             |

### Exact locale overlays

All 17 should be first-class resolved keys.

| Locale  | Base structured grammar | `abbr2words` routing |
| ------- | ----------------------- | -------------------- |
| `en_GB` | `en`                    | exact                |
| `en_IN` | `en`                    | exact                |
| `en_NG` | `en`                    | exact                |
| `en_US` | `en`                    | exact                |
| `es_CO` | `es`                    | exact                |
| `es_CR` | `es`                    | exact                |
| `es_GT` | `es`                    | exact                |
| `es_MX` | `es`                    | exact                |
| `es_NI` | `es`                    | exact                |
| `es_VE` | `es`                    | exact                |
| `fr_BE` | `fr`                    | exact                |
| `fr_CH` | `fr`                    | exact                |
| `fr_DZ` | `fr`                    | exact                |
| `pt_BR` | `pt`                    | exact                |
| `zh_CN` | `zh`                    | exact                |
| `zh_HK` | `zh`                    | exact                |
| `zh_TW` | `zh`                    | exact                |

---

## 15. File-by-file implementation plan

### `spokenform/language.py`

This is the primary refactor.

Changes:

- stop deriving global language support from the Kokoro profile;
- derive or define the 49-family + 17-overlay global registry;
- keep integration-profile languages separate;
- add `supported_languages(include_locales=...)`;
- validate language at the normalization boundary;
- use exact `abbr2words` resolution;
- retain strict `num2words` resolution;
- preserve compatibility aliases;
- document `kk -> kz` dependency translation.

Suggested exported concepts:

```python
SUPPORTED_BASE_LANGUAGES
SUPPORTED_LOCALES
KOKOROG2P_PROFILE_LANGUAGES

base_language
normalize_language
supported_languages
supports_language
language_support
resolve_abbr2words_language
resolve_num2words_language
supports_profile
```

### `spokenform/language_support.py` — recommended new module

Use this module for capability metadata if `language.py` becomes overloaded.

Responsibilities:

- `LanguageSupport`;
- number backend availability;
- structured support flags;
- sequence-policy flags;
- numeric punctuation flags;
- Kokoro integration flags;
- documentation-friendly discovery.

Keep pure identifier resolution in `language.py`.

### `spokenform/config.py`

Changes:

- separate generic number policy from Kokoro policy;
- make generic number policy capability-driven;
- keep `for_kokorog2p()` behavior stable;
- do not infer structured support from global registry membership.

### `spokenform/number_words.py`

Changes:

- add non-throwing number-backend resolution;
- keep strict direct rendering APIs strict;
- retain `cn2an` for Chinese;
- cache capability checks if beneficial;
- do not claim stable `num2words` support for `hi`, `hy`, `mn` when converter entries are absent.

### `spokenform/numbers.py`

Changes:

- remove the 17-language global-support gate;
- allow integer cardinal normalization where a backend exists;
- preserve punctuation-bearing lexemes when punctuation policy is absent;
- remove dependence on English fallback semantics;
- retain existing reviewed special behavior.

### `spokenform/numeric_lexeme.py`

Changes:

- remove generic English speech/punctuation fallback;
- represent “no reviewed decimal policy” explicitly;
- allow separator-free integer parsing independently;
- resolve exact locale policy first, then base policy;
- preserve ambiguous separator input.

### `spokenform/structured.py`

Changes:

- replace “all non-CJK languages receive shared recognizers” with an explicit capability set;
- retain fail-closed locale dispatch for languages without a locale module;
- optionally replace the long import chain with an explicit module mapping, but do not make that cleanup a prerequisite if it increases migration risk.

Possible future structure:

```python
_LOCALE_MODULES = {
    "en": "spokenform.locales.en",
    ...
}
```

### `spokenform/sequences.py`

Changes:

- split explicit sequence support from global language support;
- optionally use the number backend to produce digit names where safe;
- define a neutral/no-name punctuation policy for foundation languages;
- never silently select English punctuation vocabulary;
- preserve `SequenceFallbackMode.PRESERVE`.

### `spokenform/recognizers/sequences.py`

Changes:

- audit English fallback mappings;
- gate recognizers by reviewed capability;
- return no candidate when locale speech realization is unavailable;
- preserve existing output for current reviewed languages.

This audit is required before claiming that `prepare()` is total across the expanded registry.

### `spokenform/abbreviations.py`

Mostly unchanged.

It already delegates dependency resolution.

Once `resolve_abbr2words_language()` is corrected, custom abbreviation registration gains proper exact-overlay behavior automatically.

Add exact-overlay tests.

### `spokenform/profiles.py`

No large redesign required.

Verify that a `SpeechProfile` for every target key:

- resolves successfully;
- can compile an isolated `abbr2words` expander;
- does not require a dedicated structured locale module.

### `spokenform/__init__.py`

Export new public discovery/capability functions intentionally.

Avoid exposing every internal capability set unless callers have a concrete need.

### `README.md`

Replace the current narrow language-support paragraph.

Document:

- 49 language families;
- 17 explicit overlays;
- tiered feature coverage;
- explicit language selection;
- no automatic language detection;
- link to detailed generated coverage.

### `docs/languages.md`

Convert this to a generated or mostly-generated capability matrix.

Columns should include:

- Spokenform canonical key;
- dependency key;
- exact locale/base;
- abbreviation support;
- released number backend;
- reviewed decimal policy;
- structured grammar;
- sequence spelling;
- KokoroG2P profile;
- notes.

### `docs/api.md`

Document clearly:

```python
supported_languages()
supported_languages(include_locales=True)
supports_language(...)
language_support(...)
normalize_language(...)
resolve_abbr2words_language(...)
resolve_num2words_language(...)
```

Explain the distinction between:

- Spokenform language support;
- installed numeric backend support;
- structured locale support;
- integration-profile support.

---

## 16. Test plan

### 16.1 Add a registry contract fixture

Add:

```text
tests/data/language_registry_contract.json
```

Pin:

- 49 dependency base keys;
- 17 explicit locale overlays;
- the intentional `kz <-> kk` compatibility mapping;
- unsupported examples such as `eu`.

Suggested metadata:

```json
{
  "abbr2words_minimum": "0.2.13",
  "num2words_stable": "v0.5.14",
  "num2words_master_ref": "07814cb114157f582c40a00119c2e9faba8dcee2",
  "base_keys": [],
  "locale_keys": [],
  "spokenform_dependency_aliases": {
    "kk": "kz"
  }
}
```

Do not depend at test runtime on files inside `abbr2words/tests/`; copy the contract into Spokenform's own test data.

### 16.2 Registry parity test

Add:

```text
tests/test_language_registry_parity.py
```

Assertions should include:

```python
assert len(target_dependency_bases) == 49
assert len(target_locales) == 17
assert not supports_language("eu")
```

Compare installed `abbr2words` discovery against the pinned dependency contract.

Fail loudly if a dependency upgrade changes the registry.

### 16.3 Exact locale resolution tests

Parameterize all 17 overlays.

For every overlay test:

- underscore form;
- hyphen form;
- mixed casing;
- exact normalized key;
- exact `abbr2words` routing.

Examples:

```python
("en-gb", "en_GB")
("ES-ni", "es_NI")
("pt-br", "pt_BR")
("zh-hk", "zh_HK")
```

Base-fallback examples:

```python
("fr-FR", "fr")
("de-DE", "de")
("vi-VN", "vi")
```

### 16.4 All-language pipeline smoke test

For every globally supported key:

```python
result = prepare(
    "Plain text",
    language=language,
    use_spacy=False,
)
assert result.language == expected
assert result.spoken_text
```

This test must not require a numeric backend.

Its purpose is to prove that the base pipeline is total over the registry.

### 16.5 Abbreviation backend smoke test

For every `abbr2words` key:

- dependency resolution succeeds;
- a profile expander can be constructed;
- neutral text passes through without error.

Do not invent one abbreviation token that must have a localized expansion in every language. Registry/backend instantiation is the correct universal assertion.

### 16.6 Number capability test

For every base language:

```python
support = language_support(language)
```

If `support.plain_cardinals` is true:

- `2` is converted;
- output is non-empty;
- source mapping remains valid.

If false:

- normal `prepare()` preserves `2`;
- warning explains unavailable number capability;
- a direct strict number-rendering API may raise.

This specifically protects `hi`, `hy`, and `mn` under the stable dependency contract.

### 16.7 No-English-leakage tests

For every foundation language outside reviewed structured support, use representative structured-looking inputs:

```text
1/2
3-2
v1.2.3
192.168.0.1
A+B
50%
```

Default behavior should be:

- source preserved; or
- explicitly localized by a proven capability.

Reject output containing English semantic words introduced by Spokenform merely because a language table was missing.

Do not reject English text that was already present in the source.

### 16.8 Sequence-policy tests

Change tests currently parameterized over `SUPPORTED_BASE_LANGUAGES`.

Use:

```python
SEQUENCE_POLICY_LANGUAGES
```

for tests that require explicit sequence realization.

Add a separate global-language test that verifies default sequence fallback preserves unsupported semantics without raising.

### 16.9 Kokoro profile tests

Change assertions such as:

```python
assert set(SUPPORTED_BASE_LANGUAGES) == EXPECTED_FAMILIES
```

to:

```python
assert set(KOKOROG2P_PROFILE_LANGUAGES) == EXPECTED_FAMILIES
```

This is a critical regression boundary.

Adding Dutch to Spokenform must not claim that KokoroG2P now supports Dutch.

### 16.10 Locale-module architecture tests

Do not require:

```python
importlib.import_module(f"spokenform.locales.{language}")
```

for every global language.

Require a locale module only for an explicit:

```python
STRUCTURED_LOCALE_LANGUAGES
```

set.

---

## 17. Generated documentation and CI drift checks

Add a generator:

```text
scripts/generate_language_coverage.py
```

It should produce either:

```text
docs/language-coverage.md
```

or a delimited generated section inside `docs/languages.md`.

The generator should inspect:

- Spokenform registry;
- installed `abbr2words` registry;
- installed `num2words.CONVERTER_CLASSES`;
- Chinese backend capability;
- internal structured capability set;
- internal sequence capability set;
- KokoroG2P profile set.

Add a freshness test:

```python
def test_generated_language_docs_are_fresh():
    ...
```

This prevents runtime code, README, documentation and integration tests from drifting into different definitions of “supported language”.

---

## 18. Recommended implementation sequence

### Commit 1 — Separate registry ownership from KokoroG2P

Files:

- `spokenform/language.py`
- `spokenform/__init__.py`
- `tests/test_language.py`
- `tests/test_kokorog2p_profiles.py`

Goals:

- global registry no longer derives from Kokoro;
- 49 base families are accepted;
- 17 overlays are accepted;
- Kokoro remains its current independent family set;
- `eu` remains rejected.

Do not enable new structured semantics yet.

### Commit 2 — Exact `abbr2words` locale parity

Files:

- `spokenform/language.py`
- abbreviation resolution tests
- new registry-parity tests

Goals:

- delete `_EXACT_ABBR2WORDS_LOCALES`;
- all 17 exact overlays route to `abbr2words`;
- base fallback occurs only where the exact dependency key does not exist.

### Commit 3 — Capability-aware plain cardinals

Files:

- `spokenform/number_words.py`
- `spokenform/numbers.py`
- `spokenform/config.py`
- tests

Goals:

- installed stable `num2words` languages gain integer cardinals;
- Chinese remains on `cn2an`;
- `hi`, `hy`, `mn` preserve unsupported numbers instead of crashing;
- the normal pipeline is total over all globally supported languages.

### Commit 4 — Numeric punctuation fail-closed cleanup

Files:

- `spokenform/numeric_lexeme.py`
- `spokenform/numbers.py`
- tests

Goals:

- remove generic English decimal fallback;
- separate safe integer support from reviewed decimal support;
- exact/base punctuation policies only where explicitly defined.

### Commit 5 — Structured and sequence capability gating

Files:

- `spokenform/structured.py`
- `spokenform/sequences.py`
- `spokenform/recognizers/sequences.py`
- related tests

Goals:

- newly admitted languages cannot enter English-default semantic renderers accidentally;
- default residual sequence behavior preserves;
- opt-in spelling degrades without English punctuation leakage.

### Commit 6 — Documentation and generated parity checks

Files:

- `README.md`
- `docs/languages.md`
- `docs/api.md`
- coverage generator
- docs consistency tests

---

## 19. Acceptance criteria

### Registry

- [ ] Spokenform recognizes all 49 target base families.
- [ ] Spokenform recognizes all 17 target locale overlays.
- [ ] `supported_languages()` returns 49 base families.
- [ ] `supported_languages(include_locales=True)` represents all 66 dependency keys, accounting for canonical `kk` versus dependency `kz`.
- [ ] `eo` works.
- [ ] `es_NI` remains an exact overlay.
- [ ] `eu` raises.
- [ ] `pt-BR -> pt_BR`.
- [ ] `fr_FR -> fr`.
- [ ] `en_GB` remains exact.
- [ ] Kazakh `kk` / dependency `kz` mapping is explicitly tested.

### Abbreviations

- [ ] Every supported language resolves to a valid `abbr2words` registry.
- [ ] All 17 exact overlays are preserved when the dependency exposes them.
- [ ] Custom `SpeechProfile` / abbreviation registration works for every language key.
- [ ] No duplicated Spokenform abbreviation inventory is introduced.

### Numbers

- [ ] Every installed/released `num2words` base language can use safe plain cardinal conversion.
- [ ] Chinese continues using `cn2an`.
- [ ] Missing stable converters (`hi`, `hy`, `mn` in the attached stable/master comparison) do not crash normal `prepare()`.
- [ ] Missing number backends preserve source and expose capability clearly.
- [ ] Unknown numeric punctuation never falls back to English `point`.

### Structured semantics

- [ ] Existing reviewed-language behavior remains regression-compatible.
- [ ] New foundation languages do not enter unreviewed structured renderers by default.
- [ ] No English semantic fallback is emitted solely because a language lookup is missing.
- [ ] Unsupported structured forms preserve source.

### Integrations

- [ ] KokoroG2P profile language support remains independent.
- [ ] Existing KokoroG2P parity tests retain their current scope.
- [ ] Adding global Spokenform languages does not claim new Kokoro support.

### Quality

- [ ] All existing tests pass.
- [ ] New all-language smoke tests pass.
- [ ] Registry drift test passes.
- [ ] Documentation is generated or checked against runtime capability metadata.
- [ ] No mandatory spaCy dependency is introduced for baseline language support.
- [ ] No automatic language detection is introduced.

---

## 20. Public API examples after the change

### Discovery

```python
from spokenform import supported_languages

bases = supported_languages()

assert "nl" in bases
assert "pl" in bases
assert "tr" in bases
assert "uk" in bases

all_keys = supported_languages(include_locales=True)

assert "en_GB" in all_keys
assert "es_NI" in all_keys
assert "zh_TW" in all_keys
```

### Explicit language selection remains mandatory

```python
from spokenform import prepare_language

result = prepare_language(
    "2",
    language="nl",
    use_spacy=False,
)
```

Do not add automatic language detection.

### Base fallback

```python
prepare_language(
    "text",
    language="fr-FR",
)
```

resolves to base French because `fr_FR` is not an explicit registry overlay.

### Exact overlay

```python
prepare_language(
    "text",
    language="fr-CH",
)
```

preserves `fr_CH` and routes exact `abbr2words` data.

---

## 21. Non-goals for the first all-language release

Do not block registry coverage on:

- full date grammar for 49 languages;
- full time grammar for 49 languages;
- locale-perfect currency inflection;
- plural/case/gender realization for every unit;
- phone-number conventions for every country;
- localized URL spelling for every language;
- arbitrary acronym pronunciation;
- native-speaker-complete abbreviation dictionaries;
- spaCy model availability for every language;
- KokoroG2P support for all 49 languages.

Those should be added language by language behind explicit capabilities and tests.

---

## 22. Future architecture principle

The dependency direction should become:

```text
Spokenform language registry
      |
      +--> abbreviation backend capability (`abbr2words`)
      |
      +--> number backend capability (`num2words` / `cn2an`)
      |
      +--> numeric punctuation capability
      |
      +--> reviewed structured-locale capability
      |
      +--> sequence-rendering capability
      |
      +--> integration profiles (KokoroG2P, future TTS adapters)
```

Not:

```text
KokoroG2P languages
      |
      +--> Spokenform supported languages
```

Spokenform should remain independently useful as a general written-to-spoken normalization layer for completely different TTS systems.

---

## 23. Final implementation direction

The safest useful first release of full language coverage is intentionally conservative:

- **all 49 base families + 17 overlays are valid Spokenform inputs;**
- **all receive exact/base `abbr2words` routing;**
- **all installed released numeric backends are used for safe cardinal conversion;**
- **Chinese continues through `cn2an`;**
- **current-master-only numeric languages can still use the registry/abbreviation pipeline and preserve unsupported numbers;**
- **existing reviewed languages keep specialized structured behavior;**
- **new languages fail closed for unreviewed semantics;**
- **KokoroG2P remains an independent integration profile.**

This is real multilingual expansion rather than a registry-only change that
accidentally exposes unreviewed English defaults.
