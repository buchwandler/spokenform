from pathlib import Path

import tomllib


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
