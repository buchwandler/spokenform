# Command-line interface

Pass text as arguments or through standard input:

```bash
spokenform --lang de "Prof. Klein hat 2 kg."
echo "There are 2 tests." | spokenform --lang en
```

Use `--changes` for stage provenance and `--json` for a structured result:

```bash
spokenform --lang de --changes "Prof. Klein hat 2 kg."
spokenform --lang de --json "Prof. Klein hat 2 kg."
```

Select an installed spaCy model with `--spacy-model`. `--strict` turns an unavailable
model or invalid protected range into an error. Without strict mode, recoverable
warnings are printed to standard error for plain-text output and included in
structured output.

```bash
spokenform --lang en --spacy-model en_core_web_sm --strict "The board is 2 in. wide."
```

Pipeline stages can be disabled independently with `--no-structured`,
`--no-abbreviations`, `--no-numbers`, and `--keep-whitespace`. Structured values
remain available when lexical abbreviation expansion is disabled.

Residual symbol behavior is explicit:

```bash
spokenform --lang en --symbol-mode none 'ABC, test!'
spokenform --lang en --symbol-mode remove 'ABC, test!'
spokenform --lang en --symbol-mode keep --keep-symbols ':;,()-,.' 'ABC, test!'
spokenform --lang en --generic-acronym-case lower 'ABC AAPL'
```

`--keep-symbols` is an exact-codepoint allowlist and is meaningful only with
`--symbol-mode keep`; quote it in shells because characters such as `;` have
special syntax.
