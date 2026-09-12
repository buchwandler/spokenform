---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.3.7
kind: added
summary:
  Added registry-backed language and locale support with capability-aware numeric
  and sequence policies
status: accepted
audience: null
scopes: []
source_refs:
  - git:e5b009cd4e66768a9f5304eded1ad9b5158e9d59
paths:
  - 01_todo.md
  - README.md
  - docs/api.md
  - docs/language-coverage.md
  - docs/languages.md
  - scripts/generate_language_coverage.py
  - spokenform/__init__.py
  - spokenform/api.py
  - spokenform/cli.py
  - spokenform/config.py
  - spokenform/fallback.py
  - spokenform/language.py
  - spokenform/language_support.py
  - spokenform/locales/fr.py
  - spokenform/number_words.py
  - spokenform/numbers.py
  - spokenform/numeric_lexeme.py
  - spokenform/structured.py
  - tests/data/language_registry_contract.json
  - tests/test_cjk_architecture.py
  - tests/test_docs_consistency.py
  - tests/test_kokoro_alias_adapter.py
  - tests/test_kokorog2p_profiles.py
  - tests/test_language.py
  - tests/test_language_registry_parity.py
  - tests/test_profiles.py
  - tests/test_real_kokorog2p_integration.py
  - tests/test_sequence_fallback.py
  - tests/test_sequences.py
issues: []
prs: []
sources:
  - git:e5b009cd4e66768a9f5304eded1ad9b5158e9d59
contributors: []
breaking: false
internal: false
order: 1
---
