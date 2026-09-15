---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0003
release_version: v0.4.4
kind: fixed
summary:
  Fixed French coordinate recognition for dot and comma decimal separators
  while preserving fail-closed quantity parsing
status: accepted
audience: null
scopes: []
source_refs:
  - git:24bcda3ff23b91558eb32bd5f7a648d79af0ba86
paths:
  - spokenform/locales/fr.py
  - tests/test_fr_structured.py
  - tests/test_numeric_lexeme.py
  - tests/test_sequences.py
issues: []
prs: []
sources:
  - git:24bcda3ff23b91558eb32bd5f7a648d79af0ba86
contributors: []
breaking: false
internal: false
order: 3
---
