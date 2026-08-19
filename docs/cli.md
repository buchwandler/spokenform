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

## Interpretation and domain controls

Choose the recognition evidence policy explicitly and disable specialist domains independently:

```bash
spokenform --interpretation-mode surface "final 3-2"
spokenform --interpretation-mode contextual --disable-domain chemistry "H2O"
spokenform --disable-domain biology --disable-domain sports "..."
```

`--disable-domain` is repeatable. Available values include `chemistry`, `biology`, `sports`, `finance`, `math`, `music`, `temporal`, `quantities`, `communications`, `network`, `identifiers`, `addresses`, `references`, `legal`, `social`, `geography`, and `core`. Surface mode does not use automatic spaCy context; explicit strict spaCy use is rejected.
