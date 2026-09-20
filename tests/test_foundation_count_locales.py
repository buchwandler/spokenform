from __future__ import annotations

import pytest

from spokenform import prepare
from spokenform.language_support import SupportTier, language_support
from spokenform.number_words import cardinal

COUNT_CASES = {
    "bg_BG": ("едно", "две", "три", "четири", "пет", "шест", "седем", "осем", "девет", "десет"),
    "el_GR": ("ένα", "δύο", "τρία", "τέσσερα", "πέντε", "έξι", "επτά", "οκτώ", "εννέα", "δέκα"),
    "et_EE": (
        "üks",
        "kaks",
        "kolm",
        "neli",
        "viis",
        "kuus",
        "seitse",
        "kaheksa",
        "üheksa",
        "kümme",
    ),
    "eu_ES": ("bat", "bi", "hiru", "lau", "bost", "sei", "zazpi", "zortzi", "bederatzi", "hamar"),
    "ka_GE": ("ერთი", "ორი", "სამი", "ოთხი", "ხუთი", "ექვსი", "შვიდი", "რვა", "ცხრა", "ათი"),
    "ku_TR": ("yek", "du", "sê", "çar", "pênc", "şeş", "heft", "heşt", "neh", "deh"),
    "lb_LU": ("eent", "zwee", "dräi", "véier", "fënnef", "sechs", "siwen", "aacht", "néng", "zéng"),
    "ml_IN": ("ഒന്ന്", "രണ്ട്", "മൂന്ന്", "നാല്", "അഞ്ച്", "ആറ്", "ഏഴ്", "എട്ട്", "ഒൻപത്", "പത്ത്"),
    "mr_IN": ("एक", "दोन", "तीन", "चार", "पाच", "सहा", "सात", "आठ", "नऊ", "दहा"),
    "ne_NP": ("एक", "दुई", "तिन", "चार", "पाँच", "छ", "सात", "आठ", "नौ", "दस"),
    "sq_AL": ("një", "dy", "tre", "katër", "pesë", "gjashtë", "shtatë", "tetë", "nëntë", "dhjetë"),
    "sw_CD": ("moja", "mbili", "tatu", "nne", "tano", "sita", "saba", "nane", "tisa", "kumi"),
    "ur_PK": ("ایک", "دو", "تین", "چار", "پانچ", "چھ", "سات", "آٹھ", "نو", "دس"),
}


@pytest.mark.parametrize(("language", "expected"), COUNT_CASES.items())
def test_foundation_count_stimulus(language: str, expected: tuple[str, ...]) -> None:
    assert tuple(cardinal(i, language) for i in range(1, 11)) == expected
    result = prepare(
        "1, 2, 3, 4, 5, 6, 7, 8, 9, 10.",
        language=language,
        use_spacy=False,
    )
    assert result.spoken_text == ", ".join(expected) + "."


@pytest.mark.parametrize("language", COUNT_CASES)
def test_foundation_support_contract(language: str) -> None:
    support = language_support(language)
    assert support.tier is SupportTier.FOUNDATION
    assert support.number_backend == "numeralform"
    assert support.number_language == language.split("_", 1)[0]
    assert support.plain_cardinals
    assert not support.structured
    assert not support.sequence_policy


@pytest.mark.parametrize("language", COUNT_CASES)
def test_foundation_plain_prose_is_unchanged(language: str) -> None:
    assert (
        prepare("ordinary prose", language=language, use_spacy=False).spoken_text
        == "ordinary prose"
    )
