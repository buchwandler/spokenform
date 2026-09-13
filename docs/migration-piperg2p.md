# PiperG2P integration boundary

Spokenform prepares written text for semantic speech handoff. PiperG2P remains the owner of voice configuration, tokenization, phonemization, phoneme IDs, lexicon overlays, raw Piper and eSpeak phoneme blocks, and backend compatibility. Spokenform does not import PiperG2P or add it as a runtime dependency.

## Prepared text

Use the dedicated profile and pass its output to PiperG2P:

```python
from piperg2p import phonemize_prepared
from spokenform import prepare_for_piperg2p

prepared = prepare_for_piperg2p(
    "Pay $12.50 for 2 kg.",
    language="en",
)
result = phonemize_prepared(
    prepared.spoken_text,
    language="en-us",
    config="voice.onnx.json",
)
```

`prepare_for_piperg2p()` does not detect language, load Piper configuration, tokenize, phonemize, or encode model IDs. The semantic Spokenform language and Piper voice identifier are separate explicit choices.

## Number ownership

The Piper profile uses Spokenform's generic reviewed numeric capability model because PiperG2P consumes already-prepared text. Reviewed structured languages use `STRUCTURED_AND_PLAIN`, released plain-cardinal languages use `PLAIN`, and caller-managed families remain `NONE`. This differs from the Kokoro profile's historical handoff policy. The compatibility alias `number_policy_for_language()` remains the Kokoro policy.

## Raw phoneme blocks

PiperG2P owns parsing of raw `[[ ... ]]` blocks. Parse them with PiperG2P, convert the returned source coordinates to `ProtectedSpan`, and let Spokenform normalize only the surrounding text:

```python
from piperg2p import RawPhonemeSegment, parse_raw_blocks
from spokenform import ProtectedSpan, prepare_for_piperg2p

source = "Use 2 kg [[ tɛst ]] today."
protected = [
    ProtectedSpan(
        segment.source_start,
        segment.source_end,
        kind="piperg2p-raw-phonemes",
    )
    for segment in parse_raw_blocks(source)
    if isinstance(segment, RawPhonemeSegment)
]
prepared = prepare_for_piperg2p(
    source,
    language="en",
    protected_spans=protected,
)
```

Spokenform does not parse, interpret, or rewrite the raw block. The caller passes the resulting `spoken_text` to the Piper path that supports raw phoneme segments. A synthetic `text` voice does not parse eSpeak markup and should not be used to phonemize the raw block itself.

## Piper overrides and coordinates

Spokenform source coordinates refer to the original source. Piper overrides use half-open coordinates in prepared text. Protect a caller-owned source span, prepare the text, then map it before constructing the Piper override:

```python
output_start, output_end = prepared.map_source_span(source_start, source_end)
```

Use the mapped pair for the downstream override. `PreparedText.source_replacements` and `PreparedText.offset_map` retain exact provenance for semantic replacements.

## Annotations

Source POS, tag, and lemma data must not be copied across a semantic replacement. If Piper lexicon selection needs annotations for generated words, rerun linguistic analysis on `prepared.spoken_text`, or annotate only unchanged spans whose lexical identity remains valid. Spokenform does not automatically convert its annotations into Piper `TokenAnnotation` values.

## CI contract

`tests/test_real_piperg2p_integration.py` exercises the PiperG2P source pinned by the candidate CI workflow with a synthetic minimal `text` voice configuration. It checks prepared text, source replacements, offset provenance, Piper token offsets, phoneme IDs, and raw-block protection through PiperG2P's parser. The candidate gate does not install system eSpeak or download voice assets.

Until PiperG2P is published as an installable release, CI uses the pinned GitHub source for the candidate compatibility gate. After publication, the workflow can switch to the released distribution and a released Spokenform plus released PiperG2P gate can become the persistent released-stack check.

## Dependency direction

```text
abbr2words, cn2an, numeralform ──> spokenform ──┐
                                                 ├──> application / TTS orchestration
piperg2p ────────────────────────────────────────┘
```

The application composes the independent packages. PiperG2P is not a Spokenform runtime dependency.

## Non-goals

- Spokenform does not load Piper models or voice configurations.
- Spokenform does not derive Piper voice IDs from semantic language identifiers.
- Spokenform does not generate phonemes or token IDs.
- Spokenform does not parse Piper raw blocks.
- Spokenform does not transfer source linguistic annotations across generated text.
- Piper profile support does not promise a Piper voice or backend for every language.
