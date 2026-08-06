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

Pipeline stages can be disabled with `--no-abbreviations`, `--no-numbers`, and
`--keep-whitespace`.
