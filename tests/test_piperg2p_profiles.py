from __future__ import annotations

from spokenform import (
    KOKOROG2P_PROFILE_LANGUAGES,
    NumberPolicy,
    PreparationConfig,
    ProtectedSpan,
    prepare_for_piperg2p,
    supported_profile_languages,
    supports_profile,
)


def test_piperg2p_profile_preserves_g2p_boundaries() -> None:
    config = PreparationConfig.for_piperg2p("de")

    assert config.use_spacy is False
    assert config.strip_outer_whitespace is False
    assert config.preserve_run_boundaries is True
    assert config.model_punctuation is False


def test_piperg2p_profile_owns_reviewed_numbers() -> None:
    assert PreparationConfig.for_piperg2p("de").number_policy is NumberPolicy.STRUCTURED_AND_PLAIN


def test_piperg2p_profile_uses_plain_only_policy() -> None:
    assert PreparationConfig.for_piperg2p("nl").number_policy is NumberPolicy.PLAIN


def test_piperg2p_profile_fails_closed_for_caller_managed_numbers() -> None:
    assert PreparationConfig.for_piperg2p("hi").number_policy is NumberPolicy.NONE


def test_piperg2p_wrapper_accepts_explicit_config_unchanged() -> None:
    config = PreparationConfig(
        language="de",
        use_spacy=False,
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
        number_policy=NumberPolicy.NONE,
    )

    result = prepare_for_piperg2p("2 kg", config=config)

    assert result.spoken_text == "2 kg"
    assert result.language == "de"


def test_piperg2p_wrapper_preserves_protected_spans_and_offsets() -> None:
    source = "Use 2 kg and 3 kg."
    start = source.index("2 kg")
    end = start + len("2 kg")

    result = prepare_for_piperg2p(
        source,
        language="de",
        protected_spans=[ProtectedSpan(start, end, kind="piperg2p-override")],
    )

    output_start, output_end = result.map_source_span(start, end)
    assert result.spoken_text[output_start:output_end] == "2 kg"
    assert any(item.source == "3 kg" for item in result.source_replacements)


def test_profile_discovery_is_additive_and_backend_agnostic() -> None:
    assert supports_profile("de", "piperg2p")
    assert supports_profile("nl", "piperg2p")
    assert not supports_profile("unknown", "piperg2p")
    assert not supports_profile("en", "unknown-profile")
    assert supported_profile_languages("kokorog2p") == KOKOROG2P_PROFILE_LANGUAGES
    assert "de" in supported_profile_languages("piperg2p")
    assert supported_profile_languages("unknown-profile") == frozenset()


def test_adapter_projection_schema_remains_engine_neutral() -> None:
    result = prepare_for_piperg2p("2 kg", "de")

    assert set(result.to_adapter_dict()) == {
        "spoken_text",
        "language",
        "source_replacements",
        "offset_map",
        "warnings",
        "protected_spans",
        "reserved_spans",
        "stage_report",
    }
