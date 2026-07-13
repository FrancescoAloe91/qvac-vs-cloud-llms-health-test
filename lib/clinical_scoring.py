"""Multi-dimensional clinical KPI engine.

Scores what models *mean* across diagnosis, urgency, and management — not
whether they used the same words. Designed for fair comparison when each
LLM writes with different length, structure, and language.
"""

from __future__ import annotations

import re
from itertools import combinations

from lib import embeddings

# Hints that a numbered/bullet line is a diagnosis, not an action item.
_CONDITION_HINT = re.compile(
    r"(?:itis|osis|emia|pathy|algia| syndrome| infarct| embol| fracture|"
    r"appendicitis|appendicite|pneumonia|meningitis|gastroenteritis|"
    r"adenitis|adenite|diverticul|angina|STEMI|NSTEMI|dissection|"
    r"infection|infezione|diabetes|epileps|sclerosi|sclerosis|"
    r"manic|depressive|psychosis|bipolar|nephritis|anemia|sepsis|"
    r"pericarditis|pneumothorax|appendic|cholecyst|pancreatitis|"
    r"probabil|likely|most likely|principal|primary|diagnosis|diagnosi)",
    re.IGNORECASE,
)

_ACTION_HINT = re.compile(
    r"(?:^|\b)(?:NPO|obtain|order|perform|consult|refer|administer|"
    r"monitor|repeat|schedule|flag|document|keep|start|give|avoid|ensure|"
    r"consider|involve|screen|evaluate|assess|"
    r"richiedere|valutare|consultare|eseguire|somministrare|"
    r"ECG|troponin|ultrasound|CT scan|urinalysis|labs?\b|IV fluids?|"
    r"toxicology|mood stabilizer|psychiatric|surgical)",
    re.IGNORECASE,
)

_MANAGEMENT_HEADER = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:\**)\s*(?:"
    r"immediate (?:priorities|actions|steps|management)|"
    r"recommended (?:tests|workup|investigations)|"
    r"next steps|management(?: plan)?|treatment(?: plan)?|"
    r"tests?(?: to (?:order|obtain))?|work[- ]?up|monitoring|follow[- ]?up|"
    r"azioni immediate|gestione immediata|"
    r"esami(?: da (?:richiedere|fare))?|piano (?:terapeutico|d.azione)|"
    r"gestione|terapia)\s*[:\-–]?\s*",
    re.IGNORECASE,
)


def _clean_item(item: str) -> str:
    item = re.sub(r"\*+", "", item).strip()
    item = re.sub(
        r"\s*[-–(]\s*(ALTA|MOLTO ALTA|MODERATA|BASSA|HIGH|VERY HIGH|MODERATE|LOW)\b.*$",
        "",
        item,
        flags=re.I,
    )
    item = re.sub(r"\s*—\s*(most likely|highest probability|probable).*$", "", item, flags=re.I)
    return item.strip()


def find_best_diagnosis_list(text: str) -> list[str]:
    """Find the numbered/bullet block that best looks like a differential list.

    Scans the *whole* answer — not only the first header section — so Claude
    answers where narrative prose precedes the real list still score correctly.
    """
    if not text:
        return []

    blocks: list[tuple[int, list[str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        num_match = re.match(r"^(\d+)[\.\)]\s*(.+)", line)
        bullet_match = re.match(r"^[-•*]\s*(.+)", line)
        if num_match or bullet_match:
            block_items = []
            j = i
            while j < len(lines):
                ln = lines[j].strip()
                nm = re.match(r"^(\d+)[\.\)]\s*(.+)", ln)
                bm = re.match(r"^[-•*]\s*(.+)", ln)
                if nm:
                    block_items.append(_clean_item(nm.group(2)))
                    j += 1
                elif bm and not re.match(r"^\d", ln):
                    block_items.append(_clean_item(bm.group(1)))
                    j += 1
                else:
                    break
            if len(block_items) >= 2:
                med_score = sum(
                    1 for it in block_items
                    if _CONDITION_HINT.search(it) and not _ACTION_HINT.search(it[:40])
                )
                blocks.append((med_score, block_items))
            i = j
        else:
            i += 1

    if not blocks:
        return []

    blocks.sort(key=lambda x: x[0], reverse=True)
    best_score, best_items = blocks[0]
    if best_score == 0:
        return []

    out = []
    for item in best_items:
        if len(item) >= 4 and item not in out:
            out.append(item[:120])
    return out[:6]


def extract_management_section(text: str) -> str:
    """Extract tests, next steps, and management plan text."""
    if not text:
        return ""
    header = _MANAGEMENT_HEADER.search(text)
    if header:
        start = header.end()
        stop = re.search(
            r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:\**)\s*(?:urgency|urgenza|triage|"
            r"differential|diagnos|conclusion|summary|note)\b",
            text[start:],
            re.IGNORECASE,
        )
        end = start + stop.start() if stop else len(text)
        section = text[start:end].strip()
        if len(section) >= 10:
            return section[:600]
    # Fallback: collect bullet/numbered action lines anywhere in the answer
    # (Claude often uses "- Ensure safety..." under a ## header the regex missed).
    action_lines = []
    for line in text.splitlines():
        ln = line.strip()
        if not ln:
            continue
        cleaned = re.sub(r"^[-•*]\s*", "", ln)
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        cleaned = re.sub(r"\*+", "", cleaned).strip()
        if len(cleaned) < 8:
            continue
        if _CONDITION_HINT.search(cleaned) and not _ACTION_HINT.search(cleaned[:50]):
            continue
        if _ACTION_HINT.search(cleaned):
            action_lines.append(cleaned)
        if len(action_lines) >= 6:
            break
    return " ".join(action_lines)[:600]


def build_clinical_profile(text: str, diagnoses: list[str], urgency: dict) -> dict:
    """Structured clinical slices used for semantic KPI comparison."""
    best_dx = find_best_diagnosis_list(text)
    if best_dx:
        dx = best_dx[:3]
    else:
        dx = diagnoses[:3] if diagnoses else []
    diagnosis_block = ". ".join(dx) if dx else ""
    management = extract_management_section(text)
    urgency_label = urgency.get("label") or "unknown"
    urgency_snippet = ""
    um = re.search(r"(?:URGENZA|URGENCY)\s*[:\-]?\s*([^\n]{0,120})", text, re.I)
    if um:
        urgency_snippet = um.group(0).strip()[:120]

    # Compact summary for whole-answer semantic comparison — intentionally
    # capped so verbosity (Premium tier) does not drown the signal.
    summary_parts = []
    if diagnosis_block:
        summary_parts.append(f"Diagnoses: {diagnosis_block}")
    if urgency_snippet:
        summary_parts.append(urgency_snippet)
    elif urgency_label != "unknown":
        summary_parts.append(f"Urgency: {urgency_label}")
    if management:
        summary_parts.append(f"Plan: {management[:250]}")
    summary = ". ".join(summary_parts)[:700]

    if not summary and text:
        summary = " ".join(text.split()[:80])[:700]

    return {
        "diagnosis_block": diagnosis_block[:400],
        "management": management[:400],
        "summary": summary,
        "urgency_label": urgency_label,
    }


def _pairwise_dimension_scores(keys: list, texts: dict) -> tuple[dict, dict, bool]:
    """Average semantic similarity vs every other model for one text slice."""
    scores = {k: None for k in keys}
    pairs = {k: {} for k in keys}
    any_ok = False
    for k in keys:
        sims = []
        for j in keys:
            if j == k:
                continue
            a = texts.get(k, "")
            b = texts.get(j, "")
            if not a or not b:
                pairs[k][j] = None
                continue
            sim = embeddings.semantic_similarity_pct(a, b)
            pairs[k][j] = sim
            if sim is not None:
                sims.append(sim)
                any_ok = True
        scores[k] = round(sum(sims) / len(sims), 1) if sims else None
    return scores, pairs, any_ok


def urgency_agreement_scores(keys: list, labels: dict) -> dict:
    """How well each model's declared urgency matches the group majority."""
    present = [labels[k] for k in keys if labels.get(k)]
    if not present:
        return {k: None for k in keys}
    majority = max(set(present), key=present.count)
    order = {"critical": 4, "high": 3, "moderate": 2, "low": 1, None: 0, "unknown": 0}

    def _urgency_score(label):
        if label is None or label == "unknown":
            return 50.0
        if label == majority:
            return 100.0
        diff = abs(order.get(label, 0) - order.get(majority, 0))
        if diff == 1:
            return 70.0
        if diff == 2:
            return 40.0
        return 10.0

    return {k: round(_urgency_score(labels.get(k)), 1) for k in keys}


def compute_clinical_kpis(active: dict, diagnoses: dict, urgency: dict) -> dict:
    """Compute intelligent multi-dimensional clinical KPIs for all models."""
    keys = list(active.keys())
    profiles = {}
    for k in keys:
        text = active[k].get("output", "")
        profiles[k] = build_clinical_profile(text, diagnoses.get(k, []), urgency.get(k, {}))

    dx_scores, dx_pairs, dx_ok = _pairwise_dimension_scores(
        keys, {k: profiles[k]["diagnosis_block"] for k in keys}
    )
    mgmt_scores, mgmt_pairs, mgmt_ok = _pairwise_dimension_scores(
        keys, {k: profiles[k]["management"] for k in keys}
    )
    summary_scores, summary_pairs, summary_ok = _pairwise_dimension_scores(
        keys, {k: profiles[k]["summary"] for k in keys}
    )
    urg_scores = urgency_agreement_scores(keys, {k: profiles[k]["urgency_label"] for k in keys})

    semantic_available = dx_ok or mgmt_ok or summary_ok

    # Per-model composite — weights favour meaning over exact wording.
    composite = {}
    for k in keys:
        parts = []
        weights = []
        for val, w in [
            (dx_scores.get(k), 0.35),
            (mgmt_scores.get(k), 0.25),
            (summary_scores.get(k), 0.25),
            (urg_scores.get(k), 0.15),
        ]:
            if val is not None:
                parts.append(val * w)
                weights.append(w)
        composite[k] = round(sum(parts) / sum(weights), 1) if weights else 0.0

    return {
        "available": semantic_available,
        "profiles": profiles,
        "diagnosis_semantic": dx_scores,
        "management_semantic": mgmt_scores,
        "summary_semantic": summary_scores,
        "urgency_agreement": urg_scores,
        "composite": composite,
        "pairs": {
            "diagnosis": dx_pairs,
            "management": mgmt_pairs,
            "summary": summary_pairs,
        },
    }
