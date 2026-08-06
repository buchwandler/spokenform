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
