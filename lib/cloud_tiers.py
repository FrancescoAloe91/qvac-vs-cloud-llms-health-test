"""Editable cloud model version labels (shown on cards, charts, exports)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from lib.tiers import CLOUD_KEYS, MODEL_CONFIG

_TIERS_PATH = Path(__file__).resolve().parent.parent / "data" / "cloud_tiers.json"

DEFAULT_TIER_LABELS: Dict[str, str] = {
    "chatgpt": "5.5 Instant (chatgpt.com — default new chat)",
    "claude": "Sonnet 5 · Medium",
    "gemini": "3.5 Flash · extended thinking",
    "qvac": "",
}


def _qvac_runtime_label() -> str:
    from lib import medpsy

    return medpsy.runtime_tier_label()


def effective_tier_labels(labels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Merge saved cloud labels with live QVAC runtime info from Ollama/MedPsy setup."""
    data = dict(labels or load_tier_labels())
    data["qvac"] = _qvac_runtime_label()
    return data


def _blank_defaults() -> Dict[str, str]:
    return {k: "" for k in DEFAULT_TIER_LABELS}


def load_tier_labels() -> Dict[str, str]:
    labels = dict(DEFAULT_TIER_LABELS)
    if _TIERS_PATH.is_file():
        try:
            raw = json.loads(_TIERS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key in ("chatgpt", "claude", "gemini"):
                    val = raw.get(key)
                    if isinstance(val, str) and val.strip():
                        labels[key] = val.strip()
        except (json.JSONDecodeError, OSError):
            pass
    labels["qvac"] = _qvac_runtime_label()
    return labels


def save_tier_labels(labels: Dict[str, str]) -> None:
    _TIERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chatgpt": (labels.get("chatgpt") or DEFAULT_TIER_LABELS.get("chatgpt", "")).strip(),
        "claude": (labels.get("claude") or DEFAULT_TIER_LABELS.get("claude", "")).strip(),
        "gemini": (labels.get("gemini") or DEFAULT_TIER_LABELS.get("gemini", "")).strip(),
        "qvac": _qvac_runtime_label(),
    }
    _TIERS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def tier_label(model_key: str, labels: Optional[Dict[str, str]] = None) -> str:
    data = effective_tier_labels(labels)
    if model_key == "qvac":
        return data.get("qvac", "")
    return (data.get(model_key) or DEFAULT_TIER_LABELS.get(model_key, "")).strip()


def display_model_name(model_key: str, labels: Optional[Dict[str, str]] = None) -> str:
    base = MODEL_CONFIG.get(model_key, {}).get("name", model_key)
    tier = tier_label(model_key, labels)
    return f"{base} · {tier}" if tier else base


def short_chart_label(model_key: str, labels: Optional[Dict[str, str]] = None) -> str:
    """Compact label for tight chart cells (gauges, bars)."""
    from lib.metrics import TABLE_MODEL_SHORT

    short = TABLE_MODEL_SHORT.get(model_key, MODEL_CONFIG.get(model_key, {}).get("name", model_key))
    tier = tier_label(model_key, labels)
    if not tier:
        return short
    hint = tier.split("(")[0].strip()
    if model_key == "qvac":
        hint = hint.replace("MedPsy-4B-GGUF", "MedPsy-4B").replace(" · Ollama", " ·")
    if len(hint) > 28:
        hint = hint[:26] + "…"
    return f"{short} ({hint})" if hint else short
