from __future__ import annotations

from benchmarks import proteno as cli


def test_candidate_oracle_flag_reaches_evaluator(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(cli, "selected_languages", lambda language: ("en",))
    monkeypatch.setattr(cli, "ensure_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "load_cases_with_exclusions", lambda *args, **kwargs: ((), ()))

    def fake_evaluate_and_write(*args, **kwargs):
        calls.append(kwargs)
        return tmp_path, {
            "profile": "default",
            "normalize_literals": False,
            "cases": 0,
            "excluded_count": 0,
        }

    monkeypatch.setattr(cli, "evaluate_and_write", fake_evaluate_and_write)

    assert cli.main(["--offline", "--candidate-oracle", "--results-dir", str(tmp_path)]) == 0
    assert calls[0]["candidate_oracle"] is True
