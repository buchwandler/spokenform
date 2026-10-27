---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 3
entry_id: entry-0001
release_version: v0.4.6
kind: added
summary: Added localized speech for lexical slash compounds such as open/close
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0088
paths:
  - spokenform/recognizers/sequences.py
  - spokenform/sequences.py
  - tests/test_lexical_slash.py
  - README.md
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 1
---

The recognizer replaces the whole alphabetic compound with a localized slash word, while leaving fractions, dates, URLs, paths, units, exchange pairs, and other structured forms to their own rules.
