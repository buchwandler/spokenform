from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from spokenform import prepare
from spokenform.diagnostics import trace_structured_candidates
from spokenform.evidence import EvidenceSession


@dataclass(frozen=True)
class Segment:
    text: str
    known: bool
    frequency_rank: int | None = None


@dataclass(frozen=True)
class Word:
    text: str
    known: bool
    frequency_rank: int | None = None
    frequency_count: int | None = None
    has_lowercase: bool = True
    has_titlecase: bool = False
    has_uppercase: bool = False


@dataclass(frozen=True)
class Cue:
    text: str
    start: int = 0
    end: int = 0
    distance: int = 1
    weight: float = 0.8


@dataclass(frozen=True)
class Domain:
    score: float
    cues: tuple[Cue, ...]


class FakeEvidence:
    language = "en"
    capabilities = ("lexical", "semantic")

    def __init__(self) -> None:
        self.words: dict[str, int] = {}
        self.segments: dict[str, int] = {}
        self.domains: dict[str, int] = {}

    def word(self, word: str) -> Word:
        self.words[word] = self.words.get(word, 0) + 1
        if word.casefold() == "gpt":
            return Word(word, True, has_lowercase=False, has_uppercase=True)
        if word.casefold() in {"chat", "site"}:
            return Word(word, True)
        return Word(word, False)

    def segment(self, text: str, *, max_word_length: int = 32) -> tuple[Segment, ...]:
        self.segments[text] = self.segments.get(text, 0) + 1
        if text.casefold() == "chatgpt":
            return (Segment("chat", True), Segment("gpt", False))
        if text.casefold() in {"chat", "site"}:
            return (Segment(text, True),)
        if text.casefold() == "xyz":
            return (Segment("xyz", False),)
        return ()

    def supports_domain(
        self,
        text: str,
        *,
        target: tuple[int, int],
        domain: str,
        window: int = 6,
        decay: float = 0.7,
        threshold: float = 0.4,
    ) -> Domain | None:
        key = f"{domain}:{target}"
        self.domains[key] = self.domains.get(key, 0) + 1
        if domain in {"computing", "sports"}:
            cue = "compiler" if domain == "computing" else "semifinal"
            return Domain(0.8, (Cue(cue),))
        return None


class LexicalOnlyEvidence(FakeEvidence):
    capabilities = ("lexical",)

    def supports_domain(self, *args: object, **kwargs: object) -> Domain | None:
        raise AssertionError("semantic lookup must not run without semantic capability")


def test_provider_none_is_a_noop_and_existing_url_behavior_remains() -> None:
    source = "Visit https://example.com/page1."
    assert (
        prepare(source, use_spacy=False).to_dict()
        == prepare(source, use_spacy=False, lexical_evidence=None).to_dict()
    )
    assert prepare(source, use_spacy=False, normalize_literals=True).spoken_text == (
        "Visit h t t p s colon slash slash example dot com slash p a g e one."
    )


def test_provider_language_and_capability_validation() -> None:
    provider = FakeEvidence()
    provider.language = "de"
    with pytest.raises(ValueError, match="language mismatch"):
        prepare("chatgpt.com", language="en", lexical_evidence=provider)
    provider.language = "en_US"
    assert (
        prepare(
            "chatgpt.com", language="en", normalize_literals=True, lexical_evidence=provider
        ).spoken_text
        == "chat g p t dot com"
    )
    with pytest.raises(ValueError, match="lexical.*capability"):
        prepare(
            "chatgpt.com",
            lexical_evidence=type("NoLexical", (), {"language": "en", "capabilities": ()})(),
        )


def test_evidence_session_caches_each_lookup() -> None:
    provider = FakeEvidence()
    session = EvidenceSession(provider)
    assert session.segment("chatgpt") == session.segment("chatgpt")
    assert session.word("gpt") == session.word("gpt")
    assert session.supports("compiler 8.3.2", target=(9, 14), domain="computing")
    assert session.supports("compiler 8.3.2", target=(9, 14), domain="computing")
    assert provider.segments["chatgpt"] == 1
    assert provider.words["gpt"] == 1
    assert provider.domains["computing:(9, 14)"] == 1


def test_lexical_host_rendering_is_conservative() -> None:
    provider = FakeEvidence()
    assert (
        prepare(
            "chatgpt.com", normalize_literals=True, use_spacy=False, lexical_evidence=provider
        ).spoken_text
        == "chat g p t dot com"
    )
    assert (
        prepare(
            "https://www.chatgpt.com",
            normalize_literals=True,
            use_spacy=False,
            lexical_evidence=provider,
        ).spoken_text
        == "h t t p s colon slash slash w w w dot chat g p t dot com"
    )
    assert (
        prepare(
            "site.fr", normalize_literals=True, use_spacy=False, lexical_evidence=provider
        ).spoken_text
        == "site dot f r"
    )
    assert (
        prepare(
            "foobarbaz.com", normalize_literals=True, use_spacy=False, lexical_evidence=provider
        ).spoken_text
        == "foobarbaz dot com"
    )
    assert (
        prepare(
            "xyz.com", normalize_literals=True, use_spacy=False, lexical_evidence=provider
        ).spoken_text
        == "x y z dot com"
    )
    assert (
        prepare(
            "chat-gpt.com", normalize_literals=True, use_spacy=False, lexical_evidence=provider
        ).spoken_text
        == "chat hyphen g p t dot com"
    )


def test_url_literal_policy_and_protection_still_win() -> None:
    provider = FakeEvidence()
    source = "https://chatgpt.com"
    assert prepare(source, use_spacy=False, lexical_evidence=provider).spoken_text == source
    assert (
        prepare(
            source,
            normalize_literals=True,
            use_spacy=False,
            lexical_evidence=provider,
            protected_spans=[(0, len(source))],
        ).spoken_text
        == source
    )


def test_contextual_versions_use_positive_computing_evidence_only() -> None:
    provider = FakeEvidence()
    assert (
        "eight dot three dot two"
        in prepare("compiler 8.3.2", use_spacy=False, lexical_evidence=provider).spoken_text
    )
    assert (
        "eight dot three dot two"
        in prepare("8.3.2 compiler", use_spacy=False, lexical_evidence=provider).spoken_text
    )
    surface = prepare(
        "compiler 8.3.2", use_spacy=False, interpretation_mode="surface", lexical_evidence=provider
    )
    assert surface.spoken_text == "compiler 8.3.2"
    ipv4 = prepare("127.0.0.1", use_spacy=False, lexical_evidence=provider)
    assert any(item.rule == "sequence.ipv4" for item in ipv4.source_replacements)
    assert not any(item.rule == "sequence.version" for item in ipv4.source_replacements)
    unchanged = prepare("compiler 8.3.2", use_spacy=False, lexical_evidence=LexicalOnlyEvidence())
    assert not any(item.rule == "sequence.version" for item in unchanged.source_replacements)


def test_contextual_version_respects_domain_policy_and_sports_evidence() -> None:
    provider = FakeEvidence()
    disabled = prepare(
        "compiler 8.3.2",
        use_spacy=False,
        lexical_evidence=provider,
        disabled_domains={"identifiers"},
    )
    assert not any(item.rule == "sequence.version" for item in disabled.source_replacements)
    sports = prepare("semifinal 2-1", use_spacy=False, lexical_evidence=provider)
    assert any(item.rule == "sequence.sports" for item in sports.source_replacements)
    surface = prepare(
        "semifinal 2-1", use_spacy=False, lexical_evidence=provider, interpretation_mode="surface"
    )
    assert not any(item.rule == "sequence.sports" for item in surface.source_replacements)


def test_diagnostics_keep_contextual_evidence_and_source_details() -> None:
    records = trace_structured_candidates(
        "compiler 8.3.2", language="en", lexical_evidence=FakeEvidence()
    )
    version = next(item for item in records if item.rule == "sequence.version")
    assert version.evidence == "contextual"
    assert version.evidence_source == "lexhint:computing"
    assert version.evidence_score == 0.8
    assert version.evidence_cues == ("compiler",)


def test_real_lexhint_runtime_contract(tmp_path: Path) -> None:
    pytest.importorskip("lexhint")
    from lexhint import Lexicon
    from lexhint.builder import build_dictionary

    source = tmp_path / "kaikki-mini.jsonl"
    source.write_text(
        "\n".join(
            [
                '{"word":"chat","lang_code":"en","pos":"noun","senses":[{"glosses":["talk"]}]}',
                '{"word":"GPT","lang_code":"en","pos":"proper noun","senses":[{"glosses":["model"]}]}',
                '{"word":"compiler","lang_code":"en","pos":"noun","senses":[{"glosses":["program"],"topics":["computing"]}]}',
                '{"word":"semifinal","lang_code":"en","pos":"noun","senses":[{"glosses":["match"],"topics":["sports"]}]}',
            ]
        ),
        encoding="utf-8",
    )
    artifact, _ = build_dictionary(
        "en", source, output=tmp_path / "runtime.sqlite3", profile="runtime", no_frequency=True
    )
    lexicon = Lexicon.from_path(artifact)
    assert "lexical" in lexicon.capabilities
    assert "semantic" in lexicon.capabilities
    assert callable(lexicon.word)
    assert callable(lexicon.segment)
    assert callable(lexicon.supports_domain)
    segments = lexicon.segment("chatgpt")
    assert segments[0].text == "chat" and segments[0].known
    assert segments[1].text == "gpt" and not segments[1].known
    assert lexicon.word("gpt").uppercase_only
    assert (
        prepare(
            "chatgpt.com", normalize_literals=True, use_spacy=False, lexical_evidence=lexicon
        ).spoken_text
        == "chat g p t dot com"
    )
    assert (
        "eight dot three dot two"
        in prepare("compiler 8.3.2", use_spacy=False, lexical_evidence=lexicon).spoken_text
    )
    assert any(
        item.rule == "sequence.sports"
        for item in prepare(
            "semifinal 2-1", use_spacy=False, lexical_evidence=lexicon
        ).source_replacements
    )
