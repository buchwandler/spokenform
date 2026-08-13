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


def test_declared_package_files_exist() -> None:
    root = Path(__file__).parents[1]
    assert (root / "NOTICE").is_file()
    assert (root / "MANIFEST.in").is_file()
    assert (root / "spokenform" / "py.typed").is_file()
    assert (root / "tests" / "data" / "golden_s0.json").is_file()


def test_abbr2words_minimum_matches_structured_identity_contract() -> None:
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    dependencies = project["dependencies"]

    assert "abbr2words>=0.2.8,<0.3.0" in dependencies
    assert not any("abbr2words>=0.2.2" in requirement for requirement in dependencies)


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
