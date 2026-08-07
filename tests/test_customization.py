from concurrent.futures import ThreadPoolExecutor

import abbr2words

from spokenform import PreparationConfig, TokenAnnotation, prepare


def test_shared_custom_abbreviation_is_used_and_removed() -> None:
    expander = abbr2words.get_shared_expander("de")
    expander.add_custom_abbreviation("Kok.", "Kokorog", description="adapter test")
    try:
        result = prepare("Kok.", config=PreparationConfig.for_kokorog2p("de"))
        assert result.spoken_text == "Kokorog"
        assert result.source_edits[0].rule == "abbr:Kok."
    finally:
        assert expander.remove_abbreviation("Kok.")

    assert prepare("Kok.", config=PreparationConfig.for_kokorog2p("de")).spoken_text == "Kok."


def test_context_guard_and_language_expanders_remain_isolated() -> None:
    expander = abbr2words.get_shared_expander("de")
    expander.add_custom_abbreviation("Guard.", "Guard expansion", only_if_pos="NOUN")
    try:
        assert (
            prepare(
                "Guard. text",
                config=PreparationConfig.for_kokorog2p("de"),
                annotations=(TokenAnnotation(0, 6, text="Guard.", pos="VERB"),),
            ).spoken_text
            == "Guard. text"
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            german = list(
                pool.map(
                    lambda _: (
                        prepare("Guard.", config=PreparationConfig.for_kokorog2p("de")).spoken_text
                    ),
                    range(4),
                )
            )
            czech = list(
                pool.map(
                    lambda _: (
                        prepare("Guard.", config=PreparationConfig.for_kokorog2p("cs")).spoken_text
                    ),
                    range(4),
                )
            )
        assert german == ["Guard expansion"] * 4
        assert czech == ["Guard."] * 4
    finally:
        expander.remove_abbreviation("Guard.")
