from __future__ import annotations

from benchmarks import polynorm as cli


def test_candidate_oracle_flag_reaches_evaluator(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(cli, "selected_locales", lambda locale: ("en-US",))
    monkeypatch.setattr(cli, "ensure_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "load_cases", lambda *args, **kwargs: ())

    def fake_evaluate_and_write(*args, **kwargs):
        calls.append(kwargs)
        return tmp_path, {"profile": "default", "normalize_literals": False, "cases": 0}

    monkeypatch.setattr(cli, "evaluate_and_write", fake_evaluate_and_write)

    assert (
        cli.main(
            [
                "--offline",
                "--candidate-oracle",
                "--report",
                "none",
                "--results-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert calls[0]["candidate_oracle"] is True
    assert calls[0]["report"] == "none"
