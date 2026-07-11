"""Confronto automatico delle diagnosi tra output dei modelli."""

import re
from collections import Counter
from itertools import combinations

from lib import embeddings

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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


# Real structured answers (ChatGPT/Claude in particular) very often lead with
# an "immediate priorities / recommended tests" numbered list *before* the
# actual differential diagnosis. If we just grab the first numbered list in
# the whole text, that action-item list gets mistaken for the diagnosis —
# and since the primary diagnosis drives both the consensus-accuracy and the
# semantic-similarity KPI, this alone can crater an otherwise-correct
# answer's score. So: look for an explicit "differential diagnosis" style
# header first and scope the extraction to that section; only fall back to
# scanning the whole text if no such header exists.
_DIAGNOSIS_HEADER = re.compile(
    r"(?:differential diagnos[ie]s|likely diagnos[ie]s|most likely diagnosis|"
    r"top diagnos[ie]s|probable diagnos[ie]s|primary diagnosis|"
    r"clinical impression|impression|assessment(?: and plan)?|"
    r"diagnosi differenziale|diagnosi principale|diagnosi pi[uù] probabile|"
    r"ipotesi diagnostic[ah])\s*[:\-–]?\s*",
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


def _diagnosis_section(text: str):
    """Slice of `text` right after a diagnosis-labeled header, stopping at the
    next section header (tests/plan/urgency/...) if any. Returns ``None`` if
    no explicit diagnosis header is found."""
    header = _DIAGNOSIS_HEADER.search(text)
    if not header:
        return None
    start = header.end()
    stop = _SECTION_STOP_HEADER.search(text, start)
    end = stop.start() if stop else len(text)
    section = text[start:end].strip()
    return section or None


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
                if len(item) > 8 and item not in found:
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


def extract_keywords(text: str) -> set[str]:
    """Estrae keyword mediche rilevanti da un testo."""
    words = re.findall(r"[a-zA-Zàèéìòù]{4,}", text.lower())
    return {w for w in words if w not in _MEDICAL_STOP and len(w) > 3}


def jaccard_similarity(a: set, b: set) -> float:
    """Jaccard overlap between two keyword sets, perceptually recalibrated.

    Raw bag-of-words Jaccard on short clinical text is much harsher than
    real clinical agreement — two paraphrased answers about the very same
    diagnosis can still share few exact words. The ratio is stretched with
    a square root: 0 stays 0, 1 stays 1, ordering between models is fully
    preserved, but partial overlap reads closer to how a clinician would
    actually judge "these two mostly agree" instead of looking like a
    near-failing score.
    """
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    raw = len(a & b) / len(union)
    return raw ** 0.5


def diagnosis_overlap(diag_a: list[str], diag_b: list[str]) -> float:
    """Similarita' tra due liste di diagnosi (keyword Jaccard media)."""
    if not diag_a or not diag_b:
        return 0.0
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


def compare_with_gold_standard(gold_text: str, diagnoses: dict, keys: list) -> dict:
    """Confronta ogni modello con la diagnosi di riferimento clinica certa.

    Usa il testo incollato dall'utente (es. patologia reale anonimizzata o referto)
    come ground truth per calcolare scostamenti rispetto alla verità di riferimento.
    """
    gold_diagnoses = extract_diagnoses(gold_text)
    if not gold_diagnoses and gold_text.strip():
        gold_diagnoses = [gold_text.strip()[:300]]

    gold_primary_kw = extract_keywords(gold_diagnoses[0]) if gold_diagnoses else set()
    gold_all_kw = extract_keywords(gold_text)
    gold_primary_text = gold_diagnoses[0] if gold_diagnoses else gold_text.strip()[:300]

    accuracy_primary = {}
    coverage_ddx = {}
    semantic_accuracy = {}
    semantic_available = False

    for k in keys:
        model_diags = diagnoses.get(k, [])
        if not model_diags:
            accuracy_primary[k] = 0.0
            coverage_ddx[k] = 0.0
            semantic_accuracy[k] = None
            continue

        primary_kw = extract_keywords(model_diags[0])
        if gold_primary_kw:
            accuracy_primary[k] = round(
                jaccard_similarity(primary_kw, gold_primary_kw) * 100, 1
            )
        else:
            accuracy_primary[k] = 0.0

        if gold_diagnoses:
            coverage_ddx[k] = diagnosis_overlap(model_diags, gold_diagnoses)
        else:
            model_kw = extract_keywords(" ".join(model_diags))
            coverage_ddx[k] = round(
                jaccard_similarity(model_kw, gold_all_kw) * 100, 1
            ) if gold_all_kw else 0.0

        sim = embeddings.semantic_similarity_pct(". ".join(model_diags[:2]), gold_primary_text)
        semantic_accuracy[k] = sim
        if sim is not None:
            semantic_available = True

    return {
        "gold_diagnoses": gold_diagnoses,
        "accuracy_primary": accuracy_primary,
        "coverage_ddx": coverage_ddx,
        "gold_keywords": sorted(gold_primary_kw),
        "semantic_accuracy": semantic_accuracy,
        "semantic_available": semantic_available,
    }


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

    final = compute_final_scores(active, diagnoses, keywords)
    semantic = compute_semantic_scores(active, diagnoses)

    use_gold = bool(gold_standard_text and gold_standard_text.strip())
    gold_compare = None
    if use_gold:
        gold_compare = compare_with_gold_standard(
            gold_standard_text.strip(), diagnoses, list(active.keys())
        )

    urgency = {k: extract_urgency(v["output"]) for k, v in active.items()}
    labels = [u["label"] for u in urgency.values() if u["label"]]
    urgency_agreement = 0.0
    urgency_majority_label = None
    if labels:
        label_counts = Counter(labels).most_common(1)[0]
        urgency_majority_label = label_counts[0]
        urgency_agreement = round(label_counts[1] / len(labels) * 100, 1)

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
        "reliability": final["reliability"],
        "reliability_pairs": final["reliability_pairs"],
        "accuracy_consensus": final["accuracy_consensus"],
        "accuracy_pairs": final["accuracy_pairs"],
        "primary_keywords": final["primary_keywords"],
        "consensus_keywords": final["consensus_keywords"],
        "consensus_keyword_counts": final["consensus_keyword_counts"],
        "semantic_similarity": semantic["scores"],
        "semantic_pairs": semantic["pairs"],
        "semantic_available": semantic["available"],
        "primary_diagnosis_text": semantic["primary_text"],
        "urgency": urgency,
        "urgency_agreement": urgency_agreement,
        "urgency_majority_label": urgency_majority_label,
        "mode": "gold_standard" if use_gold else "consensus",
        "gold": gold_compare,
    }


def compute_final_scores(active: dict, diagnoses: dict, keywords: dict = None) -> dict:
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
