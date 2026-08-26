"""Command-line entry point for the Spokenform Gold benchmark."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spokenform import __version__ as SPOKENFORM_VERSION

from .compare_common import configuration_hash
from .spokenform_gold_adapter import prepare_gold_record
from .spokenform_gold_data import (
    SPOKENFORM_GOLD_COMMIT,
    SPOKENFORM_GOLD_REPOSITORY,
    ensure_data,
    load_gold_module,
    metadata_path,
    source_path,
)


@dataclass(frozen=True, slots=True)
class GoldSource:
    gold_root: Path
    source_root: Path | None
    repository: str
    commit: str | None
    mode: str
    cache_dir: Path | None


def _finite_gate(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("gate must be a finite number") from exc
    if not math.isfinite(parsed) or not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("gate must be a finite number between 0 and 1")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Spokenform against the pinned Spokenform Gold benchmark."
    )
    parser.add_argument("--gold-root", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/spokenform-gold"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument(
        "--split",
        choices=("corpus", "test", "dev", "all"),
        default="corpus",
        help=(
            "Gold selection. Automatic v2 data uses the unsplit corpus; "
            "test/dev are retained for explicit legacy split releases."
        ),
    )
    parser.add_argument("--language")
    parser.add_argument("--locale")
    parser.add_argument("--category")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--profile", choices=("gold-v1",), default="gold-v1")
    parser.add_argument("--mode", choices=("canonical", "accepted"), default="canonical")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("benchmark-results/spokenform-gold"),
    )
    parser.add_argument("--report", choices=("html", "none"), default="html")
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--gate", type=_finite_gate)
    return parser


def _load_gold_benchmark(source_root: Path | None = None) -> Any:
    if source_root is not None:
        return load_gold_module("spokenform_gold.benchmark", source_root=source_root)
    try:
        return importlib.import_module("spokenform_gold.benchmark")
    except (ModuleNotFoundError, ImportError) as exc:
        raise ModuleNotFoundError(
            "spokenform_gold is required for an explicit --gold-root release. "
            "Install the matching Gold scorer package or use automatic cache mode."
        ) from exc


def _source_commit() -> str:
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _gold_split(split: str) -> str | None:
    return None if split in {"corpus", "all"} else split


def _validate_split_for_manifest(split: str, manifest: dict[str, Any]) -> None:
    release_format = manifest.get("format")
    if release_format == "v2" and split not in {"corpus", "all"}:
        raise ValueError(
            "Spokenform Gold v2 is an unsplit corpus release; use --split corpus or --split all"
        )
    if release_format != "v2" and split == "corpus":
        raise ValueError("--split corpus requires a v2 Spokenform Gold corpus release")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _canonical_expected(record: dict[str, Any], result: dict[str, Any]) -> str | None:
    expected = result.get("expected_output")
    if expected is not None:
        return str(expected)

    oracle = record.get("oracle")
    if isinstance(oracle, dict):
        canonical = oracle.get("canonical_output")
        if canonical is not None:
            return str(canonical)

    legacy = record.get("expected_output")
    return None if legacy is None else str(legacy)


def _source_benchmarks(record: dict[str, Any]) -> list[str]:
    observations = record.get("source_observations")
    if isinstance(observations, list):
        values = {
            str(observation["benchmark"])
            for observation in observations
            if isinstance(observation, dict)
            and isinstance(observation.get("benchmark"), str)
            and observation["benchmark"]
        }
        if values:
            return sorted(values)

    legacy = record.get("source")
    if isinstance(legacy, dict) and isinstance(legacy.get("benchmark"), str):
        return [legacy["benchmark"]]

    return []


def _resolve_gold_source(args: argparse.Namespace) -> GoldSource:
    if args.gold_root is not None:
        if args.refresh:
            raise ValueError("--refresh cannot be combined with --gold-root")
        root = args.gold_root.expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"explicit Spokenform Gold release does not exist: {root}")
        return GoldSource(
            gold_root=root,
            source_root=None,
            repository="explicit local release",
            commit=None,
            mode="explicit-root",
            cache_dir=None,
        )
    release = ensure_data(
        cache_dir=args.cache_dir,
        offline=args.offline,
        refresh=args.refresh,
    )
    return GoldSource(
        gold_root=release,
        source_root=source_path(args.cache_dir),
        repository=SPOKENFORM_GOLD_REPOSITORY,
        commit=SPOKENFORM_GOLD_COMMIT,
        mode="auto-cache",
        cache_dir=args.cache_dir,
    )


def _metadata_for_source(source: GoldSource) -> dict[str, Any]:
    if source.mode == "auto-cache" and source.cache_dir is not None:
        return json.loads(metadata_path(source.cache_dir).read_text(encoding="utf-8"))
    return {
        "repository": source.repository,
        "source_commit": source.commit,
        "release_version": None,
    }


def _build_rows(
    summary: dict[str, Any], records: Iterable[dict[str, Any]], *, mode: str
) -> tuple[dict[str, Any], ...]:
    record_by_id = {record["id"]: record for record in records if isinstance(record.get("id"), str)}
    result_rows: list[dict[str, Any]] = []
    for result in summary["summary"].get("record_results", []):
        record = record_by_id.get(result["id"], {})
        units = record.get("units", [])
        source_benchmarks = _source_benchmarks(record)
        result_rows.append(
            {
                "id": result["id"],
                "family_id": record.get("family_id"),
                "language": record.get("language", result.get("language")),
                "locale": record.get("locale", result.get("locale")),
                "status": record.get("status", result.get("status")),
                "categories": sorted(
                    {unit.get("category") for unit in units if unit.get("category")}
                ),
                "source_benchmarks": source_benchmarks,
                "source_benchmark": ", ".join(source_benchmarks),
                "input": record.get("input", result.get("input")),
                "expected": _canonical_expected(record, result),
                "accepted_variants": list(result.get("accepted_variants", [])),
                "actual": result.get("prediction", ""),
                "canonical_match": bool(result.get("canonical_match")),
                "accepted_match": bool(result.get("accepted_match")),
                "primary_match": bool(
                    result.get("accepted_match" if mode == "accepted" else "canonical_match")
                ),
                "negative_for": list(record.get("negative_for", [])),
                "source_observations": (
                    list(record.get("source_observations", []))
                    if isinstance(record.get("source_observations"), list)
                    else [],
                ),
                "units": units,
            }
        )
    return tuple(sorted(result_rows, key=lambda row: row["id"]))


def _enrich_summary(
    summary: dict[str, Any], args: argparse.Namespace, source: GoldSource
) -> dict[str, Any]:
    source_metadata = _metadata_for_source(source)
    filters = {
        "split": args.split,
        "language": args.language,
        "locale": args.locale,
        "category": args.category,
        "case_ids": sorted(args.cases or []),
    }
    configuration = {
        "split": args.split,
        "language": args.language,
        "locale": args.locale,
        "category": args.category,
        "case_ids": sorted(args.cases or []),
        "profile": args.profile,
        "mode": args.mode,
        "source_mode": source.mode,
    }
    dataset_identity = source.commit or summary["gold_manifest_hash"]
    summary["selection"] = args.split
    summary["adapter"] = {
        "benchmark": "Spokenform Gold",
        "repository": source_metadata.get("repository", source.repository),
        "dataset_commit": source.commit,
        "source_mode": source.mode,
        "cache_dir": str(source.cache_dir) if source.cache_dir else None,
        "gold_root": str(source.gold_root),
        "report": args.report,
        "filters": filters,
    }
    summary["identity"] = {
        "benchmark": "Spokenform Gold",
        "dataset_commit": dataset_identity,
        "gold_manifest_hash": summary["gold_manifest_hash"],
        "spokenform_source_commit": summary["spokenform_commit"],
        "spokenform_version": summary["spokenform_version"],
        "profile": summary["profile_name"],
        "mode": summary["mode"],
        "split": summary["split"],
        "configuration_hash": configuration_hash(configuration),
    }
    return summary


def evaluate_and_write(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    source = _resolve_gold_source(args)
    benchmark = _load_gold_benchmark(source.source_root)
    verification = benchmark.verify_release(source.gold_root)
    if not args.download_only:
        _validate_split_for_manifest(args.split, verification.get("manifest", {}))
    if args.download_only:
        return source.gold_root, {"download_only": True, "source": source}
    run_dir = args.results_dir / _run_id()
    summary = benchmark.run_benchmark(
        gold_root=source.gold_root,
        split=_gold_split(args.split),
        language=args.language,
        locale=args.locale,
        category=args.category,
        case_ids=set(args.cases or []),
        prepare=prepare_gold_record,
        results_dir=run_dir,
        mode=args.mode,
        profile_name=args.profile,
        spokenform_version=SPOKENFORM_VERSION,
        spokenform_commit=_source_commit(),
    )
    _, records = benchmark.load_release_records(
        source.gold_root,
        split=_gold_split(args.split),
        language=args.language,
        locale=args.locale,
        category=args.category,
        case_ids=set(args.cases or []),
    )
    rows = _build_rows(summary, records, mode=args.mode)
    _write_jsonl(run_dir / "rows.jsonl", rows)
    summary = _enrich_summary(summary, args, source)
    _write_json(run_dir / "summary.json", summary)
    if args.report == "html":
        from .spokenform_gold_report import render_report

        render_report(summary, rows, run_dir / "report.html")
    return run_dir, summary


def _print_result(args: argparse.Namespace, run_dir: Path, summary: dict[str, Any]) -> None:
    if summary.get("download_only"):
        print(f"Spokenform Gold release: {run_dir}")
        return
    metrics = summary["summary"]
    print(
        f"Spokenform Gold source: {summary['adapter']['dataset_commit'] or 'explicit local release'}"
    )
    print(f"Gold version: {summary['spokenform_gold_version']}")
    print(f"Selection: {args.split}")
    print(f"Mode: {summary['mode']}")
    print(f"Records: {summary['record_count']}")
    print(f"Primary accuracy: {metrics['primary_accuracy']:.2%}")
    print(f"Results: {run_dir}")
    if args.report == "html":
        print(f"Report: {run_dir / 'report.html'}")
    if args.show_failures:
        print(f"Failures: {run_dir / 'failures.jsonl'}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        run_dir, summary = evaluate_and_write(args)
    except (
        FileNotFoundError,
        PermissionError,
        ValueError,
        ModuleNotFoundError,
        ImportError,
        OSError,
    ) as exc:
        raise SystemExit(f"Spokenform Gold error: {exc}") from None
    _print_result(args, run_dir, summary)
    if not summary.get("download_only") and args.gate is not None:
        if summary["summary"]["primary_accuracy"] < args.gate:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
