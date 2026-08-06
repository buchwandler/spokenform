from spokenform import normalize_numbers


def test_german_decimal_and_unit_ready_text() -> None:
    assert normalize_numbers("1,5 Kilogramm", language="de") == "eins Komma fünf Kilogramm"


def test_urls_emails_and_versions_are_protected() -> None:
    source = "Version v1.2.3: https://example.org/a2 and dev2@example.org have 2 tests."
    result = normalize_numbers(source, language="en")
    assert "v1.2.3" in result
    assert "https://example.org/a2" in result
    assert "dev2@example.org" in result
    assert "two tests" in result


def test_iso_date() -> None:
    result = normalize_numbers("2026-05-14", language="en")
    assert result == "May fourteenth, two thousand and twenty-six"


def test_currency_prefix_and_suffix() -> None:
    assert "Euro" in normalize_numbers("€12,80", language="de")
    assert "Euro" in normalize_numbers("12,80 EUR", language="de")


def test_bare_dotted_version_is_not_verbalized() -> None:
    assert normalize_numbers("Version 1.2.3", language="en") == "Version 1.2.3"
