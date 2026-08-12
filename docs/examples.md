# Examples

The repository contains executable examples in `examples/`:

- `basic.py`: minimal German normalization;
- `german.py`: German CLI with changes, JSON, and optional spaCy model;
- `english_spacy.py`: model-by-name English integration;
- `injected_pipeline.py`: application-owned spaCy pipeline;
- `protected_text.py`: caller and automatic protection;
- `offset_mapping.py`: map a source span into spoken output.

Run them from the repository root so the editable installation is found:

```bash
python examples/german.py
python examples/german.py --spacy-model de_core_news_sm
python examples/protected_text.py
```

## Interactive Jupyter notebook

The repository includes [`notebooks/spokenform_playground.ipynb`](../notebooks/spokenform_playground.ipynb).

It demonstrates:

- basic normalization;
- multilingual examples;
- structured quantities, dates, currencies, and specialist sequences;
- protected spans;
- literal normalization;
- symbol policy and generic acronym case policy;
- stage provenance;
- source/output mapping;
- an interactive `ipywidgets` playground.

A Binder badge in the main README launches the notebook directly in JupyterLab.
