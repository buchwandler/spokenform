from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).parent / "data" / "kokorog2p_semantic_transfer_manifest.json"


def test_transfer_manifest_is_valid_and_classified() -> None:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    assert {row["classification"] for row in rows} <= {
        "ported",
        "already-covered",
        "g2p-only",
    }
    assert all(row["origin"].startswith("kokorog2p:") for row in rows)
    assert all(row["reason"] for row in rows)
    assert all(row["destination"] is None or row["destination"] for row in rows)

    assert len({row["origin"] for row in rows}) == len(rows)
