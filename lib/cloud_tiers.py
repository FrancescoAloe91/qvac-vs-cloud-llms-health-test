"""Editable cloud model version labels (shown on cards, charts, exports)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from lib.tiers import CLOUD_KEYS, MODEL_CONFIG

_TIERS_PATH = Path(__file__).resolve().parent.parent / "data" / "cloud_tiers.json"

DEFAULT_TIER_LABELS: Dict[str, str] = {
    "chatgpt": "Free tier (chatgpt.com)",
    "claude": "Free tier (claude.ai)",
    "gemini": "Gemini app (gemini.google.com)",
    "qvac": "MedPsy 4B · CPU on-device",
}


def _blank_defaults() -> Dict[str, str]:
    return {k: "" for k in DEFAULT_TIER_LABELS}


def load_tier_labels() -> Dict[str, str]:
    labels = dict(DEFAULT_TIER_LABELS)
    if _TIERS_PATH.is_file():
        try:
            raw = json.loads(_TIERS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key in labels:
                    val = raw.get(key)
                    if isinstance(val, str) and val.strip():
                        labels[key] = val.strip()
        except (json.JSONDecodeError, OSError):
            pass
    return labels


def save_tier_labels(labels: Dict[str, str]) -> None:
    _TIERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: (labels.get(k) or DEFAULT_TIER_LABELS.get(k, "")).strip() for k in DEFAULT_TIER_LABELS}
    _TIERS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def tier_label(model_key: str, labels: Dict[str, str] | None = None) -> str:
    data = labels or load_tier_labels()
    return (data.get(model_key) or DEFAULT_TIER_LABELS.get(model_key, "")).strip()


def display_model_name(model_key: str, labels: Dict[str, str] | None = None) -> str:
    base = MODEL_CONFIG.get(model_key, {}).get("name", model_key)
    if model_key not in CLOUD_KEYS:
        return base
    tier = tier_label(model_key, labels)
    return f"{base} · {tier}" if tier else base


def short_chart_label(model_key: str, labels: Dict[str, str] | None = None) -> str:
    """Compact label for tight chart cells (gauges, bars)."""
    from lib.metrics import TABLE_MODEL_SHORT

    short = TABLE_MODEL_SHORT.get(model_key, MODEL_CONFIG.get(model_key, {}).get("name", model_key))
    if model_key not in CLOUD_KEYS:
        return short
    tier = tier_label(model_key, labels)
    if not tier:
        return short
    # Keep only the parenthetical / model hint when present.
    hint = tier.split("(")[0].strip()
    if len(hint) > 22:
        hint = hint[:20] + "…"
    return f"{short} ({hint})" if hint else short
