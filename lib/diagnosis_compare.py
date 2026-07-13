"""Confronto automatico delle diagnosi tra output dei modelli."""

import re
from collections import Counter
from itertools import combinations

from lib import clinical_scoring, embeddings

# Termini medici comuni per estrazione keyword
_MEDICAL_STOP = {
  # Italian
    "paziente", "anni", "della", "delle", "degli", "nella", "nelle",
    "essere", "avere", "dopo", "prima", "quando", "dove", "come",
    "diagnosi", "differenziale", "probabilita", "esami", "urgenza",
    "piano", "terapeutico", "iniziale", "richiedere", "valutare",
    # English
    "patient", "years", "history", "present", "presents", "with", "without",
    "diagnosis", "differential", "probability", "tests", "urgency", "urgent",
    "treatment", "initial", "order", "assess", "clinical", "likely",
    "moderate", "high", "very", "plan", "level", "flags",
}


# Italian ↔ English medical term pairs — normalized to the English stem so
# keyword overlap works even when QVAC answers in Italian and cloud models
# answer in English (or vice-versa). Intentionally small and high-precision:
# only terms that are unambiguous clinical equivalents, not free translation.
_MEDICAL_CANON = {
    "appendicite": "appendicitis",
    "appendicitis": "appendicitis",
    "adenite": "adenitis",
    "adenitis": "adenitis",
    "mesenterica": "mesenteric",
    "mesenteric": "mesenteric",
    "linfadenite": "lymphadenitis",
    "lymphadenitis": "lymphadenitis",
    "gastroenterite": "gastroenteritis",
    "gastroenteritis": "gastroenteritis",
    "infarto": "infarction",
    "infarction": "infarction",
    "infartu": "infarction",
    "miocardico": "myocardial",
    "miocardica": "myocardial",
    "myocardial": "myocardial",
    "coronarica": "coronary",
    "coronary": "coronary",
    "angina": "angina",
    "pericardite": "pericarditis",
    "pericarditis": "pericarditis",
    "embolia": "embolism",
    "embolism": "embolism",
    "polmonare": "pulmonary",
    "pulmonary": "pulmonary",
    "meningite": "meningitis",
    "meningitis": "meningitis",
    "encefalite": "encephalitis",
    "encephalitis": "encephalitis",
    "anafilassi": "anaphylaxis",
    "anaphylaxis": "anaphylaxis",
    "urinaria": "urinary",
    "urinary": "urinary",
    "infezione": "infection",
    "infection": "infection",
    "diverticolo": "diverticulum",
    "diverticulitis": "diverticulitis",
    "acuta": "acute",
    "acuto": "acute",
    "acute": "acute",
    "cronica": "chronic",
    "chronic": "chronic",
    "sclerosi": "sclerosis",
    "sclerosis": "sclerosis",
    "multipla": "multiple",
    "multiple": "multiple",
}


def _canonical_keyword(word: str) -> str:
    w = word.lower()
    return _MEDICAL_CANON.get(w, w)


# Real structured answers (ChatGPT/Claude in particular) very often lead with
# an "immediate priorities / recommended tests" numbered list *before* the
# actual differential diagnosis. If we just grab the first numbered list in
# the whole text, that action-item list gets mistaken for the diagnosis —
# and since the primary diagnosis drives both the consensus-accuracy and the
# semantic-similarity KPI, this alone can crater an otherwise-correct
# answer's score. So: look for an explicit "differential diagnosis" style
# header first and scope the extraction to that section; only fall back to
# scanning the whole text if no such header exists.
#
# Anchored to the start of a line (like _SECTION_STOP_HEADER below): without
# this anchor, generic words like "assessment" or "impression" match inside
# ordinary filler prose too — e.g. a ChatGPT reply that opens with "here is
# my assessment of this case" would hijack the header match before the real
# "Differential diagnosis" section even appears, and the diagnosis section
# would come back empty/garbage.
_DIAGNOSIS_HEADER = re.compile(
    r"(?:^|\n)\s*(?:#{1,3}\s*)?(?:[-•*]\s*)?(?:\**)\s*(?:differential diagnos[ie]s|likely diagnos[ie]s|"
    r"most likely diagnos[ie]s|top diagnos[ie]s|probable diagnos[ie]s|primary diagnos[ie]s|"
    r"clinical impression|assessment(?: and plan)?|"
    r"diagnosi differenziale|diagnosi principal[ei]|diagnos[ei] pi[uù] probabil[ei]|"
    r"ipotesi diagnostic[ah][ei]?)\s*[:\-–]?\s*",
    re.IGNORECASE,
)

_SECTION_STOP_HEADER = re.compile(
    r"(?:^|\n)\s*(?:\**)\s*(?:immediate (?:priorities|actions|steps)|"
    r"recommended (?:tests|workup|investigations)|next steps|"
    r"management(?: plan)?|treatment(?: plan)?|plan\b|urgency|triage|"
    r"tests?(?: to (?:order|obtain))?|work[- ]?up|monitoring|follow[- ]?up|"
    r"red flags?|esami(?: da (?:richiedere|fare))?|piano (?:terapeutico|d.azione)|"
    r"azioni immediate|urgenza|gestione)\s*[:\-–]?",
    re.IGNORECASE,
)


def _header_priority(header_match: str) -> int:
    """Higher = more specific diagnosis header. Generic 'assessment' is lowest."""
    t = header_match.lower()
    if re.search(r"differential diagnos|diagnosi differenziale", t):
        return 100
    if re.search(r"most likely diagnos|diagnos.*pi[uù] probabil", t):
        return 90
    if re.search(r"likely diagnos|probable diagnos|top diagnos", t):
        return 80
    if re.search(r"primary diagnos|diagnosi principal", t):
        return 70
    if "clinical impression" in t:
        return 50
    if re.search(r"ipotesi diagnostic", t):
        return 40
    if re.search(r"assessment", t):
        return 10
    return 20


def _diagnosis_section(text: str):
    """Best diagnosis-labeled section in `text`, not merely the first match.

    Claude (and others) often open with a generic "Assessment and plan"
    header whose body is a narrative case summary — NOT the differential
    list. The old code grabbed the *first* header match, so Claude's real
    "Most likely diagnoses:" numbered list was ignored and every KPI that
    depends on diagnoses[0] collapsed. We now scan every header, score by
    specificity, and prefer sections that actually contain a numbered list.
    """
    best_section = None
    best_prio = -1
    for header in _DIAGNOSIS_HEADER.finditer(text):
        start = header.end()
        stop = _SECTION_STOP_HEADER.search(text, start)
        end = stop.start() if stop else len(text)
        section = text[start:end].strip()
        if not section or len(section) < 6:
            continue
        prio = _header_priority(header.group(0))
        if re.search(r"(?:^|\n)\s*\d+[\.\)]", section):
            prio += 8
        if prio > best_prio:
            best_prio = prio
            best_section = section
    return best_section


def extract_diagnoses(text: str) -> list[str]:
    """Estrae voci di diagnosi differenziale da un output LLM.

    Real cloud responses (pasted by hand from ChatGPT/Claude/Gemini) rarely
    follow one fixed format, so this tries several structural patterns first
    (numbered lists, bullets, bold headers) and only falls back to a loose
    sentence-level heuristic if none of them find anything — this keeps the
    downstream KPIs from collapsing to zero just because a model wrote prose
    instead of a numbered list. If an explicit "differential diagnosis"
    header exists, that section is parsed and prioritized first so the
    primary diagnosis is never accidentally a recommended test or action
    item from an earlier list in the same response.
    """
    if not text:
        return []

    patterns = [
        r"(?:^|\n)\s*\d+[\.\)]\s*(.+?)(?=\n\s*\d+[\.\)]|\n\n|$)",
        r"(?:^|\n)\s*[-•]\s*(.+?)(?=\n[-•]|\n\n|$)",
        r"\b(?:ALTA|MOLTO ALTA|MODERATA|BASSA|HIGH|VERY HIGH|MODERATE|LOW)\b[^\n]*?[:–-]\s*(.+?)(?:\n|$)",
        r"(?:^|\n)\s*\*\*(.+?)\*\*\s*[:\-–]?\s*(.*?)(?=\n|$)",
        r"(?:most likely|probable diagnosis|likely diagnosis|top diagnosis|primary diagnosis|"
        r"diagnosi pi[uù] probabile|diagnosi principale|ipotesi diagnostica)\s*[:\-]\s*(.+?)(?:\n|\.|$)",
    ]

    def _scan(blob: str) -> list[str]:
        found = []
        for pattern in patterns:
            for match in re.finditer(pattern, blob, re.IGNORECASE | re.MULTILINE):
                item = match.group(1).strip()
                item = re.sub(r"\*+", "", item)
                item = re.sub(
                    r"\s*[-–(]\s*(ALTA|MOLTO ALTA|MODERATA|BASSA|HIGH|VERY HIGH|MODERATE|LOW)\b.*$",
                    "",
                    item,
                    flags=re.I,
                )
                if len(item) >= 4 and item not in found:
                    found.append(item[:120])
        return found

    diagnoses = []
    # Prioritize the explicitly-labeled diagnosis section (if any) so an
    # earlier "immediate priorities/tests" list never becomes diagnoses[0].
    section = _diagnosis_section(text)
    if section:
        scanned = _scan(section)
        if scanned:
            diagnoses.extend(scanned)
        else:
            # The header was found but its section is plain prose (e.g.
            # "Primary diagnosis: X" with no bullets/numbers) — split on
            # sentence/line/comma boundaries instead of falling through to
            # an unrelated numbered list elsewhere in the text.
            for chunk in re.split(r"[.\n]+", section):
                chunk = re.sub(
                    r"^\s*(?:other possibilit(?:y|ies)|altern(?:a|e)tiv[ea]s?|"
                    r"altre possibilit[aà])\s*[:\-–]\s*",
                    "",
                    chunk.strip(" ,;"),
                    flags=re.I,
                )
                for part in chunk.split(","):
                    part = part.strip()
                    if len(part) > 3 and part not in diagnoses:
                        diagnoses.append(part[:120])
    for item in _scan(text):
        if item not in diagnoses:
            diagnoses.append(item)

    # Whole-document scan: catches Claude/GPT answers where the real numbered
    # differential sits *below* a narrative "Assessment and plan" block.
    if len(diagnoses) < 2:
        fallback = clinical_scoring.find_best_diagnosis_list(text)
        for item in fallback:
            if item not in diagnoses:
                diagnoses.append(item)
    elif not clinical_scoring._CONDITION_HINT.search(diagnoses[0]):
        # Header section returned narrative prose, not conditions — prefer a
        # numbered block that actually names diagnoses.
        fallback = clinical_scoring.find_best_diagnosis_list(text)
        if fallback and clinical_scoring._CONDITION_HINT.search(fallback[0]):
            diagnoses = fallback + [d for d in diagnoses if d not in fallback]

    if not diagnoses:
        for line in text.splitlines():
            line = line.strip()
            if re.match(r"^\d+[\.\)]", line) and len(line) > 15:
                diagnoses.append(re.sub(r"^\d+[\.\)]\s*", "", line)[:120])

    if not diagnoses:
        # Loose fallback for free-form prose with no lists/bullets/bold at all:
        # keep sentences that read like a clinical statement (mention a
        # condition-sounding term) so unstructured answers aren't scored as
        # empty just because they were written as paragraphs.
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 15 and re.search(r"[a-zA-Zàèéìòù]{5,}", sentence):
                diagnoses.append(sentence[:160])
            if len(diagnoses) >= 5:
                break

    return diagnoses[:8]


def _fallback_composite(rel: float, acc: float, sem) -> float:
    if sem is None:
        return round((rel + acc) / 2, 1)
    # Legacy fallback used only when semantic clinical dimensions are unavailable.
    # Keep stable, but align weights to the unified 40/30/20/10 rule by mapping:
    # reliability -> summary-ish (10%), accuracy -> diagnosis-ish (40%), semantic -> plan-ish (30%) + urgency-ish (20%).
    # This is inherently an approximation; in normal operation we use true 4-dim weights.
    return round(rel * 0.10 + acc * 0.40 + sem * 0.50, 1)


def extract_keywords(text: str) -> set[str]:
    """Estrae keyword mediche rilevanti da un testo."""
    words = re.findall(r"[a-zA-Zàèéìòù]{3,}", text.lower())
    return {_canonical_keyword(w) for w in words if w not in _MEDICAL_STOP and len(w) > 2}


def jaccard_similarity(a: set, b: set) -> float:
    """Length-robust keyword overlap between two sets, 0-1.

    Plain Jaccard (intersection / union) has a serious blind spot for this
    use case: it silently punishes *thoroughness*. A model that writes a
    long, safety-conscious, multi-differential answer has a much bigger
    keyword set than one that writes three words — so even when every
    single concept the terse model mentioned is fully confirmed by the
    thorough one, the union balloons with the extra (still correct, still
    relevant) vocabulary and the ratio collapses. In real testing this
    made the more careful/complete cloud answers score *worse* than a
    one-line answer purely for including more detail, which is the
    opposite of what a clinically honest KPI should reward.

    Fix: blend classic Jaccard (stretched with a square root for
    perceptual calibration, as before) with the overlap coefficient
    (intersection / size of the *smaller* set), which measures "is
    everything the shorter answer said also present in the other one" and
    is insensitive to one side simply saying more. Two genuinely different
    diagnoses still score 0 either way (no shared vocabulary at all), so
    this does not create false agreement — it only stops penalizing real
    agreement that happens to be worded at different lengths.
    """
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    inter = len(a & b)
    raw_jaccard = inter / len(union)
    smaller = min(len(a), len(b))
    overlap_coef = (inter / smaller) if smaller else 0.0
    return (raw_jaccard ** 0.5 + overlap_coef) / 2


def diagnosis_overlap(diag_a: list[str], diag_b: list[str]) -> float:
    """Similarita' tra due liste di diagnosi (keyword Jaccard media).

    Only the top three items are compared so a Premium-tier answer that
    lists five extra differentials is not penalised against a terse one.
    """
    if not diag_a or not diag_b:
        return 0.0
    diag_a = diag_a[:3]
    diag_b = diag_b[:3]
    scores = []
    for da in diag_a:
        kw_a = extract_keywords(da)
        best = 0.0
        for db in diag_b:
            kw_b = extract_keywords(db)
            best = max(best, jaccard_similarity(kw_a, kw_b))
        scores.append(best)
    return round(sum(scores) / len(scores) * 100, 1)


_URGENCY_RULES = [
    (
        "critical",
        100,
        (
            "codice rosso", "code red", "life-threatening", "life threatening",
            "pericolo di vita", "emergenza vitale", "cardiac arrest", "arresto cardiaco",
            "call 911", "chiamare il 112", "immediate resuscitation",
        ),
    ),
    (
        "high",
        80,
        (
            "molto alta", "very high", "elevata", "alta", "high", "urgente", "urgent",
            "emergency", "emergenza", "emergency department", "pronto soccorso immediato",
            "immediate", "immediato", "senza indugio", "il prima possibile", "as soon as possible",
            "surgical emergency", "immediate surgical", "requires immediate", "richiede intervento immediato",
            "ricovero urgente", "immediate hospitalization", "stat ", "time-critical", "tempo critico",
        ),
    ),
    (
        "moderate",
        50,
        (
            "moderata", "moderate", "prioritaria", "priority", "differibile ma",
            "semi-urgent", "semi urgente", "should be evaluated soon", "entro poche ore",
            "within hours", "urgent but stable", "urgente ma stabile", "prompt evaluation",
        ),
    ),
    (
        "low",
        20,
        (
            "bassa", "low", "differibile", "non-emergent", "non emergent", "non urgente",
            "routine", "outpatient", "ambulatoriale", "watchful waiting", "attesa vigile",
            "follow-up", "low priority", "priorita bassa", "non e' un'emergenza", "not an emergency",
        ),
    ),
]


def extract_urgency(text: str) -> dict:
    """Estrae il livello di urgenza/triage dichiarato dal modello (0-100).

    Real answers rarely use a literal "Urgency:" label, so after checking for
    that explicit tag this also scans the whole text for common clinical
    urgency phrasing (severity order: critical > high > moderate > low) so the
    triage KPI reflects what the model actually said, not just its formatting.
    """
    if not text:
        return {"label": None, "score": None}
    lower = text.lower()

    # Negated phrasing ("non urgente", "not an emergency") would otherwise be
    # caught by the "urgente"/"emergency" substrings in the high-severity
    # rule below, so check these explicit negations first.
    _negated_low = (
        "non urgente", "non e' urgente", "non è urgente", "not urgent",
        "not an emergency", "non-emergent", "non emergent", "no e' un'emergenza",
    )
    if any(k in lower for k in _negated_low):
        return {"label": "low", "score": 20}

    match = re.search(r"(?:URGENZA|URGENCY)\s*[:\-]?\s*([^\n]{0,120})", text, re.IGNORECASE)
    if match:
        snippet = match.group(1).lower()
        for label, score, keys in _URGENCY_RULES:
            if any(k in snippet for k in keys):
                return {"label": label, "score": score}

    for label, score, keys in _URGENCY_RULES:
        if any(k in lower for k in keys):
            return {"label": label, "score": score}

    return {"label": None, "score": None}


def compute_semantic_scores(active: dict, diagnoses: dict) -> dict:
    """Similarita' di *significato* clinico tra i modelli (KPI robusto #3).

    A differenza del confronto per keyword (che penalizza due risposte che
    concordano ma usano parole diverse, es. "infarto" vs "sindrome
    coronarica acuta"), questo usa un piccolo modello di embedding eseguito
    in locale per misurare quanto le diagnosi principali si assomigliano
    nel significato, non solo nella forma. Se il servizio di embedding non
    e' raggiungibile, ritorna scores vuoti (nessun numero inventato).
    """
    keys = list(active.keys())
    primary_text = {}
    for k in keys:
        if diagnoses.get(k):
            # Join the top 2 differential items (not just the very first
            # line): a single short line is fragile input for an embedding
            # model — one slightly-off extraction can tank the whole score.
            # A couple of items give the embedding model enough clinical
            # context to anchor on the actual condition being discussed.
            primary_text[k] = ". ".join(diagnoses[k][:2])
        else:
            primary_text[k] = " ".join(active[k].get("output", "").split()[:40])

    pair_cache: dict = {}

    def _pair(a: str, b: str):
        cache_key = (a, b) if a <= b else (b, a)
        if cache_key not in pair_cache:
            pair_cache[cache_key] = embeddings.semantic_similarity_pct(
                primary_text.get(cache_key[0], ""), primary_text.get(cache_key[1], "")
            )
        return pair_cache[cache_key]

    scores = {}
    pairs = {k: {} for k in keys}
    any_available = False
    for k in keys:
        sims = []
        for j in keys:
            if j == k:
                continue
            sim = _pair(k, j)
            pairs[k][j] = sim
            if sim is not None:
                sims.append(sim)
                any_available = True
        scores[k] = round(sum(sims) / len(sims), 1) if sims else None

    return {
        "available": any_available,
        "scores": scores,
        "primary_text": primary_text,
        "pairs": pairs,
    }


def compare_with_gold_standard(
    gold_text: str,
    active: dict,
    diagnoses: dict,
    keys: list,
    urgency: dict = None,
) -> dict:
    """Confronto vs diagnosi certa — significato clinico, non ripetizione di parole.

    Confronta in modo semantico (embedding locale) diagnosi, piano/next step,
    urgenza e sintesi complessiva rispetto al testo di riferimento incollato.
    Le metriche keyword restano solo come fallback se gli embedding non sono
    disponibili.
    """
    gold_text = (gold_text or "").strip()
    gold_diagnoses = extract_diagnoses(gold_text)
    if not gold_diagnoses and gold_text:
        gold_diagnoses = [gold_text[:300]]

    gold_urgency = extract_urgency(gold_text)
    gold_profile = clinical_scoring.build_clinical_profile(
        gold_text, gold_diagnoses, gold_urgency
    )
    gold_dx_text = gold_profile["diagnosis_block"] or (
        gold_diagnoses[0] if gold_diagnoses else gold_text[:300]
    )
    gold_mgmt_text = gold_profile["management"] or gold_text[:600]
    gold_summary_text = gold_profile["summary"] or gold_text[:700]

    semantic_diagnosis = {}
    semantic_management = {}
    semantic_urgency = {}
    semantic_summary = {}
    semantic_composite = {}
    semantic_available = False

    # Legacy keyword fields — fallback only
    accuracy_primary = {}
    coverage_ddx = {}

    for k in keys:
        output = (active.get(k) or {}).get("output", "")
        model_diags = diagnoses.get(k, [])
        model_urgency = (urgency or {}).get(k) or extract_urgency(output)
        model_profile = clinical_scoring.build_clinical_profile(
            output, model_diags, model_urgency
        )

        dx_candidates_model = [
            model_profile["diagnosis_block"],
            ". ".join(model_diags[:3]) if model_diags else "",
        ]
        dx_candidates_gold = [gold_dx_text, ". ".join(gold_diagnoses[:3])]

        dx_sim = _best_semantic_similarity(dx_candidates_model, dx_candidates_gold)
        mgmt_sim = _best_semantic_similarity(
            [model_profile["management"], output[:600]],
            [gold_mgmt_text, gold_text[:600]],
        )
        summary_sim = _best_semantic_similarity(
            [model_profile["summary"], output[:700]],
            [gold_summary_text, gold_text[:700]],
        )
        urg_sim = _urgency_vs_gold(model_urgency, gold_urgency, output, gold_text)

        semantic_diagnosis[k] = dx_sim
        semantic_management[k] = mgmt_sim
        semantic_urgency[k] = urg_sim
        semantic_summary[k] = summary_sim

        if any(v is not None for v in (dx_sim, mgmt_sim, urg_sim, summary_sim)):
            semantic_available = True

        composite = _gold_semantic_composite(dx_sim, mgmt_sim, urg_sim, summary_sim)
        semantic_composite[k] = composite if composite is not None else 0.0

        # Keyword fallback (not used in composite when embeddings work)
        if model_diags and gold_diagnoses:
            primary_kw = extract_keywords(model_diags[0])
            gold_kw = extract_keywords(gold_diagnoses[0])
            accuracy_primary[k] = round(
                jaccard_similarity(primary_kw, gold_kw) * 100, 1
            ) if gold_kw else 0.0
            coverage_ddx[k] = _semantic_ddx_coverage(model_diags, gold_diagnoses)
        else:
            accuracy_primary[k] = 0.0
            coverage_ddx[k] = 0.0

    return {
        "gold_diagnoses": gold_diagnoses,
        "gold_profile": gold_profile,
        "semantic_diagnosis": semantic_diagnosis,
        "semantic_management": semantic_management,
        "semantic_urgency": semantic_urgency,
        "semantic_summary": semantic_summary,
        "semantic_composite": semantic_composite,
        "semantic_accuracy": semantic_composite,
        "semantic_available": semantic_available,
        "accuracy_primary": semantic_diagnosis if semantic_available else accuracy_primary,
        "coverage_ddx": semantic_management if semantic_available else coverage_ddx,
        "gold_keywords": sorted(extract_keywords(gold_diagnoses[0])) if gold_diagnoses else [],
    }


def _best_semantic_similarity(texts_a: list, texts_b: list):
    """Max semantic similarity across candidate text slices (paraphrase-tolerant)."""
    best = None
    for a in texts_a:
        a = (a or "").strip()
        if len(a) < 4:
            continue
        for b in texts_b:
            b = (b or "").strip()
            if len(b) < 4:
                continue
            sim = embeddings.semantic_similarity_pct(a, b)
            if sim is not None:
                best = sim if best is None else max(best, sim)
    return best


def _urgency_vs_gold(model_u: dict, gold_u: dict, model_text: str, gold_text: str):
    """Urgenza: match di livello + similarità semantica del testo di triage."""
    label_score = None
    g_label = gold_u.get("label")
    m_label = model_u.get("label")
    if g_label:
        if m_label:
            label_score = clinical_scoring.urgency_label_similarity(m_label, g_label)
        else:
            label_score = 45.0

    urg_m = re.search(
        r"(?:URGENZA|URGENCY|triage)\s*[:\-]?\s*[^\n]{0,160}",
        model_text or "",
        re.I,
    )
    urg_g = re.search(
        r"(?:URGENZA|URGENCY|triage)\s*[:\-]?\s*[^\n]{0,160}",
        gold_text or "",
        re.I,
    )
    text_sim = _best_semantic_similarity(
        [urg_m.group(0) if urg_m else model_text[:400], model_text[:400]],
        [urg_g.group(0) if urg_g else gold_text[:400], gold_text[:400]],
    )

    parts = [p for p in (label_score, text_sim) if p is not None]
    if not parts:
        return None
    if label_score is not None and text_sim is not None:
        return round(label_score * 0.55 + text_sim * 0.45, 1)
    return round(sum(parts) / len(parts), 1)


def _gold_semantic_composite(dx, mgmt, urg, summary):
    """Weighted mean of four 0–100 dimension scores (true average, not tiers)."""
    return clinical_scoring.weighted_dimension_composite(
        [
            (dx, 0.40),
            (mgmt, 0.30),
            (urg, 0.20),
            (summary, 0.10),
        ]
    ) or None


def _semantic_ddx_coverage(model_diags: list, gold_diags: list) -> float:
    """Quanto ogni voce gold è coperta semanticamente (non per keyword)."""
    if not model_diags or not gold_diags:
        return 0.0
    per_gold = []
    for gd in gold_diags[:5]:
        sims = []
        for md in model_diags[:5]:
            s = embeddings.semantic_similarity_pct(md, gd)
            if s is not None:
                sims.append(s)
        per_gold.append(max(sims) if sims else 0.0)
    return round(sum(per_gold) / len(per_gold), 1)


def compare_all(results: dict, gold_standard_text: str = None) -> dict:
    """Confronto completo tra tutti i modelli con output disponibile."""
    active = {k: v for k, v in results.items() if v.get("output")}
    diagnoses = {k: extract_diagnoses(v["output"]) for k, v in active.items()}
    keywords = {k: extract_keywords(v["output"]) for k, v in active.items()}

    # Matrice di concordanza pairwise (per etichette leggibili e per chiave modello)
    matrix = {}
    matrix_keyed = {}
    for a, b in combinations(active.keys(), 2):
        name_a = active[a].get("name", a)
        name_b = active[b].get("name", b)
        score = diagnosis_overlap(diagnoses[a], diagnoses[b])
        matrix[f"{name_a} ↔ {name_b}"] = score
        matrix_keyed[(a, b)] = score
        matrix_keyed[(b, a)] = score

    # Concordanza QVAC vs cloud (media)
    qvac_vs_cloud = []
    qvac_cloud_avg = 0.0
    if "qvac" in active and len(active) > 1:
        qvac_diags = diagnoses.get("qvac", [])
        for ck in active:
            if ck == "qvac":
                continue
            if qvac_diags:
                qvac_vs_cloud.append(diagnosis_overlap(qvac_diags, diagnoses[ck]))
            else:
                qvac_kw = keywords.get("qvac", set())
                cloud_kw = keywords.get(ck, set())
                qvac_vs_cloud.append(round(jaccard_similarity(qvac_kw, cloud_kw) * 100, 1))
        if qvac_vs_cloud:
            qvac_cloud_avg = round(sum(qvac_vs_cloud) / len(qvac_vs_cloud), 1)

    # Diagnosi primaria (prima voce) - accordo
    primary = {k: (diagnoses[k][0] if diagnoses[k] else "") for k in active}
    primary_kw = {k: extract_keywords(v) for k, v in primary.items() if v}
    primary_agreement = 0.0
    if len(primary_kw) >= 2:
        pairs = list(combinations(primary_kw.keys(), 2))
        scores = [
            jaccard_similarity(primary_kw[a], primary_kw[b]) * 100
            for a, b in pairs
        ]
        primary_agreement = round(sum(scores) / len(scores), 1)

    # Score diagnostico complessivo per modello (ricchezza + keyword density)
    model_scores = {}
    for k, v in active.items():
        diag_count = len(diagnoses[k])
        kw_count = len(keywords[k])
        richness = min(diag_count / 5, 1.0) * 50
        density = min(kw_count / 30, 1.0) * 50
        model_scores[k] = round(richness + density, 1)

    semantic = compute_semantic_scores(active, diagnoses)
    final = compute_final_scores(
        active, diagnoses, keywords, semantic_pairs=semantic.get("pairs")
    )

    urgency = {k: extract_urgency(v["output"]) for k, v in active.items()}
    clinical = clinical_scoring.compute_clinical_kpis(active, diagnoses, urgency)

    # Primary ranking KPIs — intelligent clinical dimensions (meaning, not wording).
    # Keyword overlap from `final` is kept only for the explain-score dialog.
    if clinical["available"]:
        accuracy_consensus = {
            k: clinical["diagnosis_semantic"].get(k) or final["accuracy_consensus"].get(k, 0)
            for k in active
        }
        reliability = {
            k: clinical["summary_semantic"].get(k) or final["reliability"].get(k, 0)
            for k in active
        }
        semantic_similarity = {
            k: clinical["management_semantic"].get(k)
            for k in active
        }
        clinical_composite = clinical["composite"]
    else:
        reliability = final["reliability"]
        accuracy_consensus = final["accuracy_consensus"]
        semantic_similarity = semantic["scores"]
        clinical_composite = {
            k: _fallback_composite(
                reliability.get(k, 0),
                accuracy_consensus.get(k, 0),
                semantic_similarity.get(k),
            )
            for k in active
        }

    labels = [u["label"] for u in urgency.values() if u["label"]]
    urgency_agreement = 0.0
    urgency_majority_label = None
    if labels:
        label_counts = Counter(labels).most_common(1)[0]
        urgency_majority_label = label_counts[0]
        urgency_agreement = round(label_counts[1] / len(labels) * 100, 1)

    use_gold = bool(gold_standard_text and gold_standard_text.strip())
    gold_compare = None
    if use_gold:
        gold_compare = compare_with_gold_standard(
            gold_standard_text.strip(),
            active,
            diagnoses,
            list(active.keys()),
            urgency=urgency,
        )

    return {
        "diagnoses": diagnoses,
        "matrix": matrix,
        "matrix_keyed": matrix_keyed,
        "qvac_cloud_concordance": qvac_cloud_avg,
        "primary_agreement": primary_agreement,
        "model_diagnostic_scores": model_scores,
        "diagnosis_counts": {k: len(diagnoses[k]) for k in active},
        "keyword_counts": {k: len(keywords[k]) for k in active},
        "active_count": len(active),
        "reliability": reliability,
        "reliability_pairs": final["reliability_pairs"],
        "accuracy_consensus": accuracy_consensus,
        "accuracy_pairs": final["accuracy_pairs"],
        "primary_keywords": final["primary_keywords"],
        "consensus_keywords": final["consensus_keywords"],
        "consensus_keyword_counts": final["consensus_keyword_counts"],
        "semantic_similarity": semantic_similarity,
        "semantic_pairs": semantic["pairs"],
        "semantic_available": clinical["available"] or semantic["available"],
        "primary_diagnosis_text": semantic["primary_text"],
        "clinical_composite": clinical_composite,
        "clinical_profiles": clinical.get("profiles", {}),
        "clinical_dimensions": {
            "diagnosis": clinical.get("diagnosis_semantic", {}),
            "management": clinical.get("management_semantic", {}),
            "summary": clinical.get("summary_semantic", {}),
            "urgency": clinical.get("urgency_agreement", {}),
        },
        "clinical_dimension_pairs": clinical.get("pairs", {}),
        "keyword_reliability": final["reliability"],
        "keyword_accuracy": final["accuracy_consensus"],
        "urgency": urgency,
        "urgency_agreement": urgency_agreement,
        "urgency_majority_label": urgency_majority_label,
        "mode": "gold_standard" if use_gold else "consensus",
        "gold": gold_compare,
    }


def compute_final_scores(
    active: dict,
    diagnoses: dict,
    keywords: dict = None,
    semantic_pairs: dict = None,
) -> dict:
    """KPI finali a parita' di prompt: affidabilita' e accuratezza (consenso).

    Affidabilita': quanto le diagnosi di un modello concordano con gli altri
    (inter-rater reliability proxy, 0-100%).

    Accuratezza (consenso): quanto la diagnosi primaria del modello si allinea
    al consenso della maggioranza degli altri modelli sullo stesso prompt.
    Senza ground truth clinico, il consenso inter-modello e' il miglior proxy.

    Ogni punteggio combina il confronto strutturato (liste di diagnosi
    estratte) con un confronto sul testo intero (keyword Jaccard). Questo
    evita che il punteggio di un modello collassi a zero solo perche' ha
    scritto la risposta in prosa invece di una lista numerata: il contenuto
    clinico reale resta la base del confronto anche quando la formattazione
    non aiuta il parser.
    """
    keys = list(active.keys())
    keywords = keywords or {k: extract_keywords(active[k].get("output", "")) for k in keys}
    semantic_pairs = semantic_pairs or {}

    def _pair_sem(a: str, b: str):
        return semantic_pairs.get(a, {}).get(b)

    def _blend_kw_sem(kw_score: float, a: str, b: str) -> float:
        sem = _pair_sem(a, b)
        if sem is not None:
            return round(kw_score * 0.35 + sem * 0.65, 1)
        return round(kw_score, 1)

    # Affidabilita' = media concordanza pairwise con tutti gli altri, mescolando
    # il confronto per liste (peso maggiore, quando disponibile) con quello
    # sul testo intero (fallback sempre disponibile).
    reliability = {}
    reliability_pairs = {k: {} for k in keys}
    for k in keys:
        others = [j for j in keys if j != k]
        pair_scores = []
        for j in others:
            text_score = round(jaccard_similarity(keywords.get(k, set()), keywords.get(j, set())) * 100, 1)
            if diagnoses.get(k) and diagnoses.get(j):
                list_score = diagnosis_overlap(diagnoses[k], diagnoses[j])
                pair_val = round(list_score * 0.65 + text_score * 0.35, 1)
            else:
                pair_val = text_score
            pair_val = _blend_kw_sem(pair_val, k, j)
            pair_scores.append(pair_val)
            reliability_pairs[k][j] = pair_val
        reliability[k] = round(sum(pair_scores) / len(pair_scores), 1) if pair_scores else 0.0

    # Consenso: keyword della diagnosi primaria (o, in assenza di una lista
    # riconosciuta, le prime parole della risposta).
    primary_kw = {}
    for k in keys:
        if diagnoses.get(k):
            primary_kw[k] = extract_keywords(diagnoses[k][0])
        else:
            first_chunk = " ".join(active[k].get("output", "").split()[:30])
            primary_kw[k] = extract_keywords(first_chunk)

    word_counts: Counter = Counter()
    for kw in primary_kw.values():
        for w in kw:
            word_counts[w] += 1

    n_models = len(primary_kw)
    threshold = max(2, (n_models + 1) // 2)
    # "consensus_set" (words used by a majority of models) is kept only as
    # human-readable context for the explanation dialog ("these are the
    # words most models agree on") — it is deliberately NOT the scoring
    # mechanism below anymore. A hard majority-vote-per-word threshold is a
    # cliff edge: a model can be squarely on-topic and still get an exact,
    # misleading 0% just because its specific word choice never crossed the
    # vote count, even while every other signal (reliability, semantic
    # similarity) shows it agrees with at least one peer. Accuracy is
    # therefore computed the same way reliability is — a smooth pairwise
    # average against every other model — but scoped to the primary
    # diagnosis only, so it stays a distinct signal from reliability
    # (which looks at the *whole* differential list).
    consensus_set = {w for w, c in word_counts.items() if c >= threshold}

    accuracy_consensus = {}
    accuracy_pairs = {k: {} for k in keys}
    for k, kw in primary_kw.items():
        others = [j for j in keys if j != k]
        if not others:
            accuracy_consensus[k] = 0.0
            continue
        pair_scores = []
        for j in others:
            pair_val = round(jaccard_similarity(kw, primary_kw.get(j, set())) * 100, 1)
            pair_val = _blend_kw_sem(pair_val, k, j)
            accuracy_pairs[k][j] = pair_val
            pair_scores.append(pair_val)
        accuracy_consensus[k] = round(sum(pair_scores) / len(pair_scores), 1)

    return {
        "reliability": reliability,
        "reliability_pairs": reliability_pairs,
        "accuracy_consensus": accuracy_consensus,
        "accuracy_pairs": accuracy_pairs,
        "primary_keywords": primary_kw,
        "consensus_keywords": sorted(consensus_set),
        "consensus_keyword_counts": {w: c for w, c in word_counts.items() if w in consensus_set},
    }
