# spokenform

`spokenform` is a single-language written-to-spoken text normalizer for speech
applications. It expands abbreviations and units, verbalizes structured numeric
forms, protects literal ranges, and records stage-by-stage provenance and offset
maps.

```{toctree}
:maxdepth: 2
:caption: Documentation

installation
quickstart
architecture
api
migration-kokorog2p
cli
spacy
protection
mapping
examples
limitations
google_tn
release-checklist
changelog
```

## Scope

The package accepts plain text and one selected processing language. Language
detection, mixed-language segmentation, SSMD or other markup parsing, and phoneme
generation are intentionally outside the package.
