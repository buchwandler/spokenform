# Examples

Run examples from the repository root after installing the project:

```bash
python -m pip install -e .
python examples/basic.py
python examples/german.py
python examples/protected_text.py
python examples/offset_mapping.py
```

The spaCy examples require the optional library and a trained pipeline:

```bash
python -m pip install -e ".[spacy]"
python -m spacy download de_core_news_sm
python -m spacy download en_core_web_sm
python examples/german.py --spacy-model de_core_news_sm
python examples/english_spacy.py
python examples/injected_pipeline.py
```

`spokenform` never downloads a model automatically. Applications may either pass
an already loaded pipeline with `nlp=...` or request an installed model with
`spacy_model=...`.

The spaCy examples demonstrate model loading, injection, and annotation alignment. With `abbr2words` 0.2.0, bundled rules do not yet require POS labels, so the spoken output can be unchanged unless the shared abbreviation registry contains custom POS-guarded entries.
