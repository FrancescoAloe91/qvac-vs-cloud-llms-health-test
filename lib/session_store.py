"""Persist per-case benchmark snapshots (survives refresh and top-level reset)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from lib.cases import CASE_IDS

CASE5_MAX_RUNS = 4
SLOTS_FILE = Path(__file__).resolve().parent.parent / ".case_snapshots.json"
LEGACY_SESSION_FILE = Path(__file__).resolve().parent.parent / ".session_rankings.json"


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def load_slots() -> Dict[str, dict]:
    if not SLOTS_FILE.exists():
        return _migrate_legacy()
    try:
        data = json.loads(SLOTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _migrate_legacy() -> Dict[str, dict]:
    """Best-effort import from the old list-based session file."""
    if not LEGACY_SESSION_FILE.exists():
        return {}
    try:
        history = json.loads(LEGACY_SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(history, list):
        return {}
    slots = {}
    for entry in history:
        cid = entry.get("case_id")
        if cid in CASE_IDS and cid not in slots:
            slots[cid] = {"entry": entry, "case_id": cid, "case_label": entry.get("case", cid)}
    return slots


def save_slots(slots: Dict[str, dict]) -> None:
    try:
        SLOTS_FILE.write_text(json.dumps(slots, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def clear_slots() -> None:
    save_slots({})
    if LEGACY_SESSION_FILE.exists():
        try:
            LEGACY_SESSION_FILE.unlink()
        except OSError:
            pass


def format_saved_at(iso: str, lang: str = "en") -> str:
    """Human-readable local time for slot cards (e.g. 14:32)."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def make_snapshot(
    case_id: str,
    case_label: str,
    compare: dict,
    ranking_df: pd.DataFrame,
    model_keys: list,
    lang: str,
    entry: dict,
    results: Optional[dict] = None,
    gold_standard_text: str = "",
) -> dict:
    slim_results = {}
    if results:
        for key, val in results.items():
            slim_results[key] = {
                "stats": val.get("stats"),
                "content": val.get("content", ""),
            }
    saved_at = datetime.now(timezone.utc).isoformat()
    entry = dict(entry)
    entry["saved_at"] = saved_at
    return {
        "case_id": case_id,
        "case_label": case_label,
        "compare": _sanitize(compare),
        "ranking_records": ranking_df.to_dict(orient="records"),
        "model_keys": model_keys,
        "use_gold": compare.get("mode") == "gold_standard",
        "gold_standard_text": gold_standard_text.strip() if gold_standard_text else "",
        "entry": entry,
        "lang": lang,
        "results": _sanitize(slim_results),
        "saved_at": saved_at,
    }


def slot_runs(slot_data: Optional[dict]) -> list:
    """Lista snapshot per slot — caso 5 può averne fino a CASE5_MAX_RUNS."""
    if not slot_data:
        return []
    if isinstance(slot_data.get("runs"), list):
        return [r for r in slot_data["runs"] if r]
    if slot_data.get("entry") or slot_data.get("ranking_records"):
        return [slot_data]
    return []


def slot_is_filled(slots: Dict[str, dict], case_id: str) -> bool:
    return len(slot_runs(slots.get(case_id))) > 0


def slot_run_count(slots: Dict[str, dict], case_id: str) -> int:
    return len(slot_runs(slots.get(case_id)))


def slot_latest_saved_at(slot_data: Optional[dict]) -> str:
    runs = slot_runs(slot_data)
    if not runs:
        return ""
    return runs[-1].get("saved_at") or (runs[-1].get("entry") or {}).get("saved_at") or ""


def slot_latest_snapshot(slot_data: Optional[dict]) -> Optional[dict]:
    runs = slot_runs(slot_data)
    return runs[-1] if runs else None


def ranking_df_from_snapshot(snapshot: dict) -> pd.DataFrame:
    records = snapshot.get("ranking_records") or []
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def slots_as_history(slots: Dict[str, dict]) -> list:
    """Un entry per slot — caso 5 usa entry con score mediati se multi-run."""
    from lib.metrics import build_averaged_entry_from_runs

    history = []
    for cid in CASE_IDS:
        if not slot_is_filled(slots, cid):
            continue
        data = slots[cid]
        if cid == "case5" and len(slot_runs(data)) > 1:
            entry = build_averaged_entry_from_runs(slot_runs(data))
            if entry:
                history.append(entry)
                continue
        latest = slot_latest_snapshot(data)
        if latest and latest.get("entry"):
            history.append(latest["entry"])
    return history


def save_slot(slots: Dict[str, dict], case_id: str, snapshot: dict) -> Dict[str, dict]:
    slots = dict(slots)
    snapshot = dict(snapshot)
    saved_at = datetime.now(timezone.utc).isoformat()
    snapshot["saved_at"] = saved_at
    if snapshot.get("entry"):
        entry = dict(snapshot["entry"])
        entry["saved_at"] = saved_at
        snapshot["entry"] = entry

    if case_id == "case5":
        existing = slots.get("case5", {})
        runs = slot_runs(existing)
        runs.append(snapshot)
        if len(runs) > CASE5_MAX_RUNS:
            runs = runs[-CASE5_MAX_RUNS:]
        slots["case5"] = {
            "multi_run": True,
            "case_id": "case5",
            "case_label": snapshot.get("case_label", "case5"),
            "runs": runs,
            "saved_at": saved_at,
        }
    else:
        slots[case_id] = snapshot

    save_slots(slots)
    return slots
