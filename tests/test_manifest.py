"""Tests for manifest.json rules that hassfest enforces in CI."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).parent.parent / "custom_components" / "qustodio" / "manifest.json"


def test_manifest_keys_sorted_like_hassfest() -> None:
    """Keys are domain, name, then alphabetical (hassfest rejects any other order)."""
    keys = list(json.loads(MANIFEST.read_text()))
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])
