#!/usr/bin/env python3
"""Assert ranking scores equal the documented weighted formulas."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.clinical_scoring import urgency_label_similarity, weighted_dimension_composite
from lib.metrics import (
    CONSENSUS_DIM_WEIGHTS,
    GOLD_DIM_WEIGHTS,
    _clinical_gold_score,
    _gold_dimensions,
    _weighted_from_dimensions,
    consensus_raw_score,
    format_weighted_formula,
    rescale_relative,
)


def test_weighted_composite():
    got = weighted_dimension_composite([(80.0, 0.40), (60.0, 0.30), (90.0, 0.20), (70.0, 0.10)])
    expected = round(80 * 0.40 + 60 * 0.30 + 90 * 0.20 + 70 * 0.10, 1)
    assert got == expected, f"composite {got} != {expected}"


def test_urgency_continuous():
    assert urgency_label_similarity("high", "high") == 100.0
    assert urgency_label_similarity("high", "moderate") == round(100 - (1 / 3) * 100, 1)
    assert urgency_label_similarity("critical", "low") == 0.0


def test_consensus_from_snapshot():
    import json

    snap_path = ROOT / ".case_snapshots.json"
    if not snap_path.exists():
        print("skip snapshot test — no .case_snapshots.json")
        return

    data = json.loads(snap_path.read_text())
    slot = data.get("slots", {}).get("case1") or data.get("slots", {}).get("case2")
    if not slot:
        print("skip snapshot test — no case slot")
        return

    compare = slot.get("compare") or slot.get("last_compare")
    if not compare or not compare.get("clinical_dimensions"):
        print("skip snapshot test — no compare data")
        return

    keys = [k for k in compare.get("clinical_dimensions", {}).get("diagnosis", {})]
    raw = {k: consensus_raw_score(compare, k) for k in keys}
    composite = compare.get("clinical_composite") or {}

    for k in keys:
        dims = {
            "diagnosis": compare["clinical_dimensions"]["diagnosis"].get(k),
            "management": compare["clinical_dimensions"]["management"].get(k),
            "summary": compare["clinical_dimensions"]["summary"].get(k),
            "urgency": compare["clinical_dimensions"]["urgency"].get(k),
        }
        calc = _weighted_from_dimensions(dims, CONSENSUS_DIM_WEIGHTS)
        if calc is None:
            continue
        assert calc == raw[k], f"{k}: raw {raw[k]} != calc {calc}"
        if k in composite and composite[k] is not None:
            assert abs(calc - composite[k]) < 0.15, f"{k}: composite mismatch {composite[k]} vs {calc}"

    rescaled = rescale_relative(raw)
    peak = max(raw.values())
    for k, v in raw.items():
        exp = round(v / peak * 100, 1) if peak > 0 else 0.0
        assert rescaled[k] == exp, f"{k}: rescaled {rescaled[k]} != {exp}"

    print(f"OK consensus formulas ({len(keys)} models) — example: {format_weighted_formula(dims, CONSENSUS_DIM_WEIGHTS)}")


def test_gold_formula():
    gold = {
        "semantic_available": True,
        "semantic_diagnosis": {"qvac": 85.0},
        "semantic_management": {"qvac": 70.0},
        "semantic_urgency": {"qvac": 90.0},
        "semantic_summary": {"qvac": 60.0},
        "accuracy_primary": {"qvac": 0},
        "coverage_ddx": {"qvac": 0},
    }
    dims = _gold_dimensions(gold, "qvac")
    calc = _weighted_from_dimensions(dims, GOLD_DIM_WEIGHTS)
    score = _clinical_gold_score(gold, "qvac")
    assert calc == score, f"gold {score} != calc {calc}"


def main():
    test_weighted_composite()
    test_urgency_continuous()
    test_gold_formula()
    test_consensus_from_snapshot()
    print("All score formula checks passed.")


if __name__ == "__main__":
    main()
