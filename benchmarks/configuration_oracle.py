"""Bounded diagnostic search over documented Spokenform configurations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from spokenform import PreparedText, prepare

from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

MAX_CONFIGURATIONS = 8


@dataclass(frozen=True, slots=True)
class ConfigurationVariant:
    """One documented public configuration alternative."""

    config_id: str
    overrides: tuple[tuple[str, Any], ...] = ()
    policy_expansion: bool = False

    def as_kwargs(self) -> dict[str, Any]:
        return dict(self.overrides)


CONFIGURATION_LATTICE: tuple[ConfigurationVariant, ...] = (
    ConfigurationVariant("default"),
    ConfigurationVariant("long-number-contextual", (("long_number_mode", "contextual"),)),
    ConfigurationVariant(
        "acronym-conservative-unknown",
        (("generic_acronym_mode", "conservative_unknown"),),
    ),
    ConfigurationVariant(
        "acronym-spell-unknown",
        (("generic_acronym_mode", "spell_unknown"),),
    ),
    ConfigurationVariant(
        "normalize-literals",
        (("normalize_literals", True),),
        policy_expansion=True,
    ),
    ConfigurationVariant(
        "long-number-contextual-acronym-conservative",
        (
            ("long_number_mode", "contextual"),
            ("generic_acronym_mode", "conservative_unknown"),
        ),
    ),
    ConfigurationVariant(
        "interpretation-surface",
        (("interpretation_mode", "surface"),),
    ),
    ConfigurationVariant(
        "sequence-fallback-spell",
        (("sequence_fallback_mode", "spell"),),
        policy_expansion=True,
    ),
)


@dataclass(frozen=True, slots=True)
class ConfigurationOracleAnalysis:
    """Stable per-row configuration-oracle evidence."""

    enabled: bool
    scorable: bool
    baseline_config_id: str
    best_config_id: str | None
    baseline_speech_wer: float
    best_config_speech_wer: float
    config_regret: float
    speech_equivalent: bool
    changed_stages: tuple[str, ...]
    policy_expansion: bool
    reason: str | None = None
    best_interpretation_mode: str = "contextual"


def _score(actual: str, expected: str, language: str) -> tuple[bool, float, bool]:
    equivalent = speech_key_equivalent(actual, language=language) == speech_key_equivalent(
        expected, language=language
    )
    wer = word_error_rate(speech_key(expected), speech_key(actual))
    literal_exact = literal_key(actual) == literal_key(expected)
    return equivalent, wer, literal_exact


def _stage_names(result: PreparedText) -> tuple[str, ...]:
    return tuple(stage.name for stage in result.stages if stage.changed)


def analyze_configuration_oracle(
    source: str,
    expected: str,
    baseline_result: PreparedText,
    *,
    language: str,
    prepare_fn: Callable[..., PreparedText] = prepare,
    base_kwargs: dict[str, Any] | None = None,
    variants: tuple[ConfigurationVariant, ...] = CONFIGURATION_LATTICE,
) -> ConfigurationOracleAnalysis:
    """Evaluate a small fixed lattice without changing runtime defaults."""
    if len(variants) > MAX_CONFIGURATIONS:
        raise ValueError(f"configuration lattice exceeds cap of {MAX_CONFIGURATIONS}")
    kwargs = dict(base_kwargs or {})
    kwargs.setdefault("language", language)
    baseline_equivalent, baseline_wer, baseline_literal_exact = _score(
        baseline_result.spoken_text, expected, language
    )
    scored: list[tuple[bool, float, bool, str, ConfigurationVariant, PreparedText]] = [
        (
            baseline_equivalent,
            baseline_wer,
            baseline_literal_exact,
            "default",
            ConfigurationVariant("default"),
            baseline_result,
        )
    ]
    try:
        for variant in variants:
            if variant.config_id == "default":
                continue
            result = prepare_fn(source, **kwargs, **variant.as_kwargs())
            equivalent, wer, literal_exact = _score(result.spoken_text, expected, language)
            scored.append((equivalent, wer, literal_exact, variant.config_id, variant, result))
    except Exception as exc:
        return ConfigurationOracleAnalysis(
            enabled=True,
            scorable=False,
            baseline_config_id="default",
            best_config_id=None,
            baseline_speech_wer=baseline_wer,
            best_config_speech_wer=baseline_wer,
            config_regret=0.0,
            speech_equivalent=baseline_equivalent,
            changed_stages=(),
            policy_expansion=False,
            reason=f"{type(exc).__name__}: {exc}",
        )
    winner = min(
        scored,
        key=lambda item: (not item[0], item[1], not item[2], item[3] != "default", item[3]),
    )
    _, best_wer, _, best_id, best_variant, best_result = winner
    return ConfigurationOracleAnalysis(
        enabled=True,
        scorable=True,
        baseline_config_id="default",
        best_config_id=best_id,
        baseline_speech_wer=baseline_wer,
        best_config_speech_wer=best_wer,
        config_regret=max(0.0, baseline_wer - best_wer),
        speech_equivalent=winner[0],
        changed_stages=_stage_names(best_result),
        policy_expansion=best_variant.policy_expansion,
        best_interpretation_mode=str(
            best_variant.as_kwargs().get("interpretation_mode", "contextual")
        ),
    )


def analysis_fields(analysis: ConfigurationOracleAnalysis) -> dict[str, Any]:
    """Flatten configuration evidence for benchmark rows."""
    return {
        "config_oracle_enabled": analysis.enabled,
        "config_oracle_scorable": analysis.scorable,
        "baseline_config_id": analysis.baseline_config_id,
        "best_config_id": analysis.best_config_id,
        "baseline_speech_wer": analysis.baseline_speech_wer,
        "best_config_speech_wer": analysis.best_config_speech_wer,
        "config_regret": analysis.config_regret,
        "config_oracle_speech_equivalent": analysis.speech_equivalent,
        "config_changed_stages": list(analysis.changed_stages),
        "config_policy_expansion": analysis.policy_expansion,
        "config_best_interpretation_mode": analysis.best_interpretation_mode,
        "config_oracle_reason": analysis.reason,
    }


def oracle_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate configuration headroom without mixing policy expansion into normal gains."""
    enabled = [row for row in rows if row.get("config_oracle_enabled")]
    scorable = [row for row in enabled if row.get("config_oracle_scorable")]
    normal = [row for row in scorable if not row.get("config_policy_expansion")]
    regret_sum = sum(float(row.get("config_regret", 0.0)) for row in normal)
    return {
        "schema_version": 2,
        "enabled": bool(enabled),
        "cases": len(enabled),
        "scorable_cases": len(scorable),
        "normal_configuration_cases": len(normal),
        "policy_expansion_cases": sum(bool(row.get("config_policy_expansion")) for row in scorable),
        "surface_best_count": sum(
            row.get("best_config_id") == "interpretation-surface" for row in normal
        ),
        "best_config_counts": {
            config_id: sum(row.get("best_config_id") == config_id for row in normal)
            for config_id in sorted(
                {str(row.get("best_config_id")) for row in normal if row.get("best_config_id")}
            )
        },
        "config_regret_sum": regret_sum,
        "config_regret_mean": regret_sum / len(normal) if normal else 0.0,
    }


def analyze_domain_ablations(
    source: str,
    expected: str,
    *,
    language: str,
    prepare_fn: Callable[..., PreparedText] = prepare,
    base_kwargs: dict[str, Any] | None = None,
    domains: tuple[str, ...] = ("chemistry", "biology", "math", "music", "sports"),
) -> dict[str, Any]:
    """Run targeted one-domain ablations without expanding the lattice."""
    kwargs = dict(base_kwargs or {})
    kwargs.setdefault("language", language)
    baseline = prepare_fn(source, **kwargs)
    _, baseline_wer, _ = _score(baseline.spoken_text, expected, language)
    results: dict[str, dict[str, Any]] = {}
    for domain in domains:
        ablation_kwargs = dict(kwargs)
        ablation_kwargs["disabled_domains"] = {domain}
        result = prepare_fn(source, **ablation_kwargs)
        equivalent, wer, literal_exact = _score(result.spoken_text, expected, language)
        results[domain] = {
            "speech_equivalent": equivalent,
            "speech_wer": wer,
            "literal_exact": literal_exact,
            "domain_ablation_regret": max(0.0, baseline_wer - wer),
            "improved": wer < baseline_wer,
            "fully_recovers": equivalent,
            "changed_stages": list(_stage_names(result)),
        }
    return {
        "domains": results,
        "domain_ablation_improvement_count": sum(
            bool(item["improved"]) for item in results.values()
        ),
        "domain_ablation_fully_recovers_count": sum(
            bool(item["fully_recovers"]) for item in results.values()
        ),
        "domain_ablation_by_domain": {
            domain: item["domain_ablation_regret"] for domain, item in results.items()
        },
    }


__all__ = [
    "CONFIGURATION_LATTICE",
    "MAX_CONFIGURATIONS",
    "ConfigurationOracleAnalysis",
    "ConfigurationVariant",
    "analysis_fields",
    "analyze_domain_ablations",
    "analyze_configuration_oracle",
    "oracle_aggregates",
]
