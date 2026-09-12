---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0003
release_version: 0.4.0
kind: quality
summary: Improved release hardening for the Numeralform 0.1.1 dependency boundary
status: accepted
audience: null
scopes: []
source_refs:
- tl:task-0072
paths:
- spokenform/number_words.py
- spokenform/language.py
- spokenform/language_support.py
- tests/test_number_words.py
- tests/test_language.py
- .github/workflows/tests.yml
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 3
---
Hardened numeric input validation and backend capability checks, advertised the pt_PT locale, preserved established Spokenform surface policy, and expanded the minimum-dependency migration contract tests.
