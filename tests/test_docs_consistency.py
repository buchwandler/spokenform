import re
from pathlib import Path

from spokenform.language import SUPPORTED_BASE_LANGUAGES

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).parents[1]
CURRENT_RELEASE_DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "release-checklist.md",
    ROOT / "docs" / "migration-kokorog2p.md",
)


def _abbr2words_requirement() -> tuple[str, str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirement = next(
        dependency for dependency in project["dependencies"] if dependency.startswith("abbr2words")
    )
    minimum = re.search(r">=([0-9]+(?:\.[0-9]+)*)", requirement)
    assert minimum is not None, requirement
    return requirement, minimum.group(1)


def test_current_release_docs_match_declared_abbr2words_minimum() -> None:
    requirement, minimum = _abbr2words_requirement()
    expected_minimum = f"abbr2words>={minimum}"

    for path in CURRENT_RELEASE_DOCS:
        text = path.read_text(encoding="utf-8")
        assert expected_minimum in text, path
        assert requirement in text, path


def test_policy_modes_are_documented_with_examples() -> None:
    text = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    for mode in (
        "known_only",
        "conservative_unknown",
        "spell_unknown",
        "registered_acronym_mode",
        "long_number_mode",
        "preserve",
        "contextual",
        "cardinal",
    ):
        assert mode in text
    assert "false-positive" in text
    assert "abbr2words" in text


def test_benchmark_docs_are_reachable_from_main_navigation() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    benchmark_page = (ROOT / "docs" / "benchmarks.md").read_text(encoding="utf-8")
    assert "benchmarks" in index
    assert "Historical" in index
    assert "kokorog2p-0.2.3-handoff" in index
    for document in ("polynorm", "proteno", "google_tn"):
        assert document in benchmark_page


def test_runtime_languages_are_present_in_canonical_matrix() -> None:
    matrix = (ROOT / "docs" / "languages.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", matrix, re.MULTILINE))
    assert set(SUPPORTED_BASE_LANGUAGES) <= documented

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/languages.md" in readme


def test_russian_runtime_boundaries_are_documented() -> None:
    text = (ROOT / "docs" / "languages.md").read_text(encoding="utf-8")
    for phrase in ("`ru`", "`ru_RU`", "`rus`", "caller-managed", "numeral government", "RUB"):
        assert phrase in text


def test_thai_runtime_boundaries_are_documented() -> None:
    text = (ROOT / "docs" / "languages.md").read_text(encoding="utf-8")
    for phrase in ("`th`", "th_TH", "THB", "Thai digits", "caller-managed"):
        assert phrase in text
