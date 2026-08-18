from __future__ import annotations

import hashlib
from pathlib import Path

from plant_intelligence.publication.case_study_b_pub_b2 import build_publication_assets

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pub_b2_publication_assets_are_byte_stable_across_rebuilds(tmp_path):
    out = tmp_path / "publication"

    first = build_publication_assets(ROOT, out)
    first_hashes = {name: _sha256(path) for name, path in first.items()}

    second = build_publication_assets(ROOT, out)
    second_hashes = {name: _sha256(path) for name, path in second.items()}

    assert first_hashes == second_hashes

    svg_names = [name for name in second if name.startswith("figure_0")]
    assert len(svg_names) == 4
    for name in svg_names:
        text = second[name].read_text(encoding="utf-8")
        assert "2026-08-18T16:59:51+00:00" in text
