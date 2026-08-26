import re
from pathlib import Path

import spokenform

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


def test_optional_dependencies_keep_spacy_and_remove_ssmd_and_lingua() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    optional = project["optional-dependencies"]

    assert "spacy" in optional
    assert "ssmd" not in optional
    assert "langdetect" not in optional
    assert all(
        "ssmd" not in requirement.lower() and "lingua-language-detector" not in requirement.lower()
        for requirements in optional.values()
        for requirement in requirements
    )


def test_lexhint_optional_dependency_supports_0_2_family() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    optional = project["optional-dependencies"]

    requirement = "lexhint>=0.1.2,<0.3.0"
    assert requirement in optional["lexhint"]
    assert requirement in optional["all"]


def test_declared_package_files_exist() -> None:
    root = Path(__file__).parents[1]
    assert (root / "NOTICE").is_file()
    assert (root / "MANIFEST.in").is_file()
    assert (root / "spokenform" / "py.typed").is_file()
    assert (root / "tests" / "data" / "golden_s0.json").is_file()


def test_manifest_literal_includes_exist() -> None:
    root = Path(__file__).parents[1]
    manifest = (root / "MANIFEST.in").read_text(encoding="utf-8")
    entries = re.findall(r"^include\s+([^\s#]+)\s*$", manifest, flags=re.MULTILINE)

    assert entries
    missing = [entry for entry in entries if not (root / entry).is_file()]
    assert not missing, f"MANIFEST.in includes missing files: {missing}"


def test_abbr2words_minimum_matches_structured_identity_contract() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    dependencies = project["dependencies"]

    assert "abbr2words>=0.2.10,<0.3.0" in dependencies
    assert not any("abbr2words>=0.2.2" in requirement for requirement in dependencies)


def test_abbr2words_exposes_the_conservative_initialism_policy() -> None:
    from inspect import signature

    from abbr2words import abbr2words_with_replacements

    assert "initialism_mode" in signature(abbr2words_with_replacements).parameters


def test_abbr2words_units_module_exposes_supported_unit_entries() -> None:
    from abbr2words.units import unit_entries

    entries = unit_entries("en")
    assert entries
    assert any(entry.canonical_id == "length-meter" for entry in entries)


def test_scm_version_fallback_is_neutral() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert project["tool"]["setuptools_scm"]["fallback_version"] == "0+unknown"


def test_public_exports_are_bound() -> None:
    assert spokenform.__all__
    assert all(hasattr(spokenform, name) for name in spokenform.__all__)


def test_documentation_sources_are_markdown() -> None:
    docs = Path(__file__).parents[1] / "docs"
    source_files = [
        path
        for path in docs.rglob("*")
        if path.is_file()
        and "_build" not in path.parts
        and path.name not in {"conf.py", "requirements.txt"}
    ]
    assert source_files
    assert all(path.suffix == ".md" for path in source_files)


def test_released_abbr2words_0210_cjk_contract() -> None:
    import abbr2words
    from abbr2words import abbr2words as expand_abbreviations
    from abbr2words.units import unit_entries

    version = tuple(int(part) for part in abbr2words.__version__.split(".")[:3])
    assert version >= (0, 2, 10)

    assert expand_abbreviations("㈱東京商事", lang="ja") == "株式会社東京商事"
    assert expand_abbreviations("AI", lang="ko") == "에이아이"
    assert expand_abbreviations("AI技术", lang="zh_CN") == "人工智能技术"
    assert expand_abbreviations("5 km", lang="zh_CN") == "5 公里"

    mainland_entries = unit_entries("zh_CN")
    assert len(mainland_entries) == 39
    assert any(entry.canonical_id == "currency-chinese-yuan" for entry in mainland_entries)
