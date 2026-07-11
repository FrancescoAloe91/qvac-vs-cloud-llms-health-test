"""KPI tables and diagnostic metrics."""

import pandas as pd

from lib.i18n import t
from lib.tiers import MODEL_CONFIG, TIERS

# Stima illustrativa (non misurata) del tempo medio richiesto dal flusso manuale
# cloud: apertura sito, attesa caricamento, copia prompt, incolla, attesa risposta,
# copia risposta, incolla nel riquadro. Usata solo per il KPI "tempo risparmiato".
CLOUD_MANUAL_OVERHEAD_S = 75.0

URGENCY_META = {
    "critical": {"label_key": "urgency.critical", "score": 100, "color": "#ef4444"},
    "high": {"label_key": "urgency.high", "score": 80, "color": "#f97316"},
    "moderate": {"label_key": "urgency.moderate", "score": 50, "color": "#f5c518"},
    "low": {"label_key": "urgency.low", "score": 20, "color": "#22c55e"},
    None: {"label_key": "urgency.unknown", "score": 0, "color": "#64748b"},
}


def privacy_score(is_cloud: bool) -> int:
    return 0 if is_cloud else 100


def clinical_grade_10(score_pct: float) -> float:
    """Rescale a 0-100% clinical accuracy score to a familiar 1-10 school grade.

    Only meaningful in gold-standard mode (a confirmed reference diagnosis was
    provided) — a "10" means the model's primary diagnosis matched the
    reference almost exactly in both wording/keywords and meaning, with full
    differential coverage. Without a reference there is no ground truth to
    grade against, so this is intentionally never shown in consensus-only
    mode (see build_unified_ranking).
    """
    if score_pct is None:
        return None
    return round(max(1.0, min(10.0, 1.0 + (score_pct / 100.0) * 9.0)), 1)


def _blend_score(a: float, b: float, sem, weights=(0.35, 0.35, 0.3)) -> float:
    """Blend two keyword-based metrics with an optional semantic metric.

    Semantic similarity adds real value (it catches "same diagnosis,
    different words" that pure keyword-overlap misses) but it is also the
    single noisiest signal here: it is computed from one short extracted
    snippet through a small local embedding model, so it is given a
    supporting weight rather than the deciding one — a single
    mis-extracted snippet should nudge the score, not single-handedly
    collapse it while the two more robust, multi-item signals (reliability
    and accuracy, both averaged over the *whole* differential) disagree.
    Falls back to a plain 50/50 average when embeddings are missing.
    """
    if sem is None:
        return round((a + b) / 2, 1)
    wa, wb, ws = weights
    return round(a * wa + b * wb + sem * ws, 1)


def _L(lang: str) -> dict:
    """Column label map for the active UI language."""
    return {
        "model": t("cols.model", lang),
        "tier_req": t("cols.tier_requested", lang),
        "tier": t("cols.tier", lang),
        "local": t("cols.local", lang),
        "kpi": t("cols.kpi", lang),
        "kpi_cloud": t("cols.kpi_cloud", lang),
        "kpi_local": t("cols.kpi_local", lang),
        "privacy": t("cols.privacy", lang),
        "latency": t("cols.latency", lang),
        "token_out": t("cols.token_out", lang),
        "reliability": t("cols.reliability", lang),
        "acc_consensus": t("cols.accuracy_consensus", lang),
        "score_consensus": t("cols.consensus_score", lang),
        "rank_consensus": t("cols.consensus_rank", lang),
        "acc_primary": t("cols.primary_accuracy", lang),
        "ddx_cov": t("cols.ddx_coverage", lang),
        "score_clinical": t("cols.clinical_score", lang),
        "rank_clinical": t("cols.clinical_rank", lang),
        "rank": t("cols.rank", lang),
        "score_final": t("cols.final_score", lang),
        "rel_short": t("cols.reliability_short", lang),
        "acc_cons_short": t("cols.accuracy_consensus_short", lang),
        "sem_short": t("cols.semantic_short", lang),
        "score_cons_short": t("cols.consensus_score_short", lang),
        "acc_clin_short": t("cols.clinical_accuracy", lang),
        "ddx_short": t("cols.ddx_coverage_short", lang),
        "sem_clin_short": t("cols.semantic_gold_short", lang),
        "score_clin_short": t("cols.clinical_score_short", lang),
        "grade_10": t("cols.grade_10", lang),
        "urgency": t("cols.urgency", lang),
        "urgency_score": t("cols.urgency_score", lang),
    }


def build_performance_table(results: dict, tier_key: str, lang: str = "en") -> pd.DataFrame:
    L = _L(lang)
    tier_label = TIERS[tier_key].label
    rows = []
    for key, cfg in MODEL_CONFIG.items():
        data = results.get(key, {})
        stats = data.get("stats", {})
        if cfg["cloud"]:
            rows.append(
                {
                    L["model"]: cfg["name"],
                    # No tier concept applies to cloud sites — the depth
                    # selector only ever changes QVAC's own prompt.
                    L["tier_req"]: "—",
                    "TTFT (s)": "—",
                    "TPS": "—",
                    L["latency"]: "—",
                    L["token_out"]: "—",
                    L["kpi"]: L["kpi_cloud"],
                    L["privacy"]: "0%",
                }
            )
        else:
            rows.append(
                {
                    L["model"]: cfg["name"],
                    # QVAC is the only model the depth selector actually drives.
                    L["tier_req"]: f"{tier_label} ({L['local']})",
                    # Cast to str: this column also holds "—" for cloud rows, and a
                    # mixed float/str object column breaks pandas->Arrow serialization.
                    "TTFT (s)": str(stats.get("ttft_s") or "—"),
                    "TPS": str(stats.get("tps") or stats.get("tokens_per_second") or "—"),
                    L["latency"]: str(stats.get("latency_s") or "—"),
                    L["token_out"]: str(stats.get("completion_tokens") or "—"),
                    L["kpi"]: L["kpi_local"],
                    L["privacy"]: "100%",
                }
            )
    return pd.DataFrame(rows)


def build_consensus_table(compare: dict, tier_key: str, model_keys: list, lang: str = "en") -> pd.DataFrame:
    L = _L(lang)
    tier_label = TIERS[tier_key].label
    sem_scores = compare.get("semantic_similarity", {}) or {}
    sem_available = compare.get("semantic_available", False)
    rows = []
    for key in model_keys:
        cfg = MODEL_CONFIG.get(key, {})
        if not cfg:
            continue
        rel = compare.get("reliability", {}).get(key, 0)
        acc = compare.get("accuracy_consensus", {}).get(key, 0)
        sem = sem_scores.get(key) if sem_available else None
        score = _blend_score(rel, acc, sem)
        row = {
            L["model"]: cfg["name"],
            # The depth selector only drives QVAC; cloud sites get one
            # untiered prompt no matter what, so "Tier" doesn't apply to them.
            L["tier"]: f"{tier_label} ({L['local']})" if not cfg["cloud"] else "—",
            L["reliability"]: rel,
            L["acc_consensus"]: acc,
        }
        if sem_available:
            row[L["sem_short"]] = str(sem) if sem is not None else "—"
        row[L["score_consensus"]] = score
        row[L["privacy"]] = privacy_score(cfg["cloud"])
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(L["score_consensus"], ascending=False)
        df[L["rank_consensus"]] = range(1, len(df) + 1)
    return df


def build_gold_table(compare: dict, tier_key: str, model_keys: list, lang: str = "en") -> pd.DataFrame:
    if not compare.get("gold"):
        return pd.DataFrame()

    L = _L(lang)
    tier_label = TIERS[tier_key].label
    gold = compare["gold"]
    sem_available = gold.get("semantic_available", False)
    sem_scores = gold.get("semantic_accuracy", {}) or {}
    rows = []
    for key in model_keys:
        cfg = MODEL_CONFIG.get(key, {})
        if not cfg:
            continue
        acc_p = gold["accuracy_primary"].get(key, 0)
        cov = gold["coverage_ddx"].get(key, 0)
        sem = sem_scores.get(key) if sem_available else None
        score = _blend_score(acc_p, cov, sem, weights=(0.35, 0.35, 0.3))
        row = {
            L["model"]: cfg["name"],
            L["tier"]: f"{tier_label} ({L['local']})" if not cfg["cloud"] else "—",
            L["acc_primary"]: acc_p,
            L["ddx_cov"]: cov,
        }
        if sem_available:
            row[L["sem_clin_short"]] = str(sem) if sem is not None else "—"
        row[L["score_clinical"]] = score
        row[L["grade_10"]] = clinical_grade_10(score)
        row[L["privacy"]] = privacy_score(cfg["cloud"])
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(L["score_clinical"], ascending=False)
        df[L["rank_clinical"]] = range(1, len(df) + 1)
    return df


def build_unified_ranking(compare: dict, model_keys: list, lang: str = "en") -> pd.DataFrame:
    L = _L(lang)
    use_gold = compare.get("mode") == "gold_standard" and compare.get("gold")
    sem_scores = compare.get("semantic_similarity", {}) or {}
    sem_available = compare.get("semantic_available", False)
    rows = []

    for key in model_keys:
        cfg = MODEL_CONFIG.get(key, {})
        if not cfg:
            continue

        rel = compare.get("reliability", {}).get(key, 0)
        acc_c = compare.get("accuracy_consensus", {}).get(key, 0)
        sem = sem_scores.get(key) if sem_available else None
        score_cons = _blend_score(rel, acc_c, sem)
        priv = privacy_score(cfg["cloud"])

        row = {
            "key": key,
            L["model"]: cfg["name"],
            L["rel_short"]: rel,
            L["acc_cons_short"]: acc_c,
            L["sem_short"]: sem,
            L["score_cons_short"]: score_cons,
            L["privacy"]: priv,
        }

        if use_gold:
            g = compare["gold"]
            acc_g = g["accuracy_primary"].get(key, 0)
            cov_g = g["coverage_ddx"].get(key, 0)
            sem_g = g.get("semantic_accuracy", {}).get(key) if g.get("semantic_available") else None
            score_gold = _blend_score(acc_g, cov_g, sem_g, weights=(0.35, 0.35, 0.3))
            row[L["acc_clin_short"]] = acc_g
            row[L["ddx_short"]] = cov_g
            row[L["sem_clin_short"]] = sem_g
            row[L["score_clin_short"]] = score_gold
            row[L["score_final"]] = round((score_cons + score_gold) / 2, 1)
            row[L["grade_10"]] = clinical_grade_10(score_gold)
        else:
            row[L["acc_clin_short"]] = None
            row[L["ddx_short"]] = None
            row[L["sem_clin_short"]] = None
            row[L["score_clin_short"]] = None
            row[L["score_final"]] = score_cons
            row[L["grade_10"]] = None

        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(L["score_final"], ascending=False).reset_index(drop=True)
        df[L["rank"]] = range(1, len(df) + 1)
    return df


def build_urgency_table(compare: dict, model_keys: list, lang: str = "en") -> pd.DataFrame:
    """Tabella del livello di triage/urgenza dichiarato da ciascun modello."""
    L = _L(lang)
    urgency = compare.get("urgency", {})
    rows = []
    for key in model_keys:
        cfg = MODEL_CONFIG.get(key, {})
        if not cfg:
            continue
        u = urgency.get(key, {"label": None, "score": None})
        meta = URGENCY_META.get(u.get("label"), URGENCY_META[None])
        score = u.get("score")
        rows.append(
            {
                L["model"]: cfg["name"],
                L["urgency"]: t(meta["label_key"], lang),
                # Cast to str: mixing int scores and "—" placeholders in one object
                # column breaks pandas -> Arrow serialization in st.dataframe.
                L["urgency_score"]: str(score) if score is not None else "—",
            }
        )
    return pd.DataFrame(rows)


def time_saved_seconds(qvac_latency_s) -> float:
    """Stima illustrativa del tempo risparmiato rispetto al flusso manuale cloud."""
    try:
        latency = float(qvac_latency_s)
    except (TypeError, ValueError):
        return 0.0
    return round(max(CLOUD_MANUAL_OVERHEAD_S - latency, 0.0), 1)


def build_session_entry(
    case_label: str,
    tier_label: str,
    ranking_df: pd.DataFrame,
    compare: dict,
    lang: str = "en",
) -> dict:
    """Crea uno snapshot compatto del round corrente per la session leaderboard."""
    L = _L(lang)
    if ranking_df.empty:
        return {}
    winner_row = ranking_df.iloc[0]
    return {
        "case": case_label,
        "tier": tier_label,
        "winner_key": winner_row["key"],
        "winner_name": winner_row[L["model"]],
        "winner_score": winner_row[L["score_final"]],
        "mode": compare.get("mode", "consensus"),
        "scores": {
            row["key"]: row[L["score_final"]] for _, row in ranking_df.iterrows()
        },
    }


def _verdict_key(score: float) -> str:
    if score >= 65:
        return "narrative.verdict_high"
    if score >= 40:
        return "narrative.verdict_mid"
    return "narrative.verdict_low"


def build_ranking_narrative(
    ranking_df: pd.DataFrame,
    compare: dict,
    model_keys: list,
    lang: str = "en",
    use_gold: bool = False,
) -> list:
    """Genera una sintesi scritta automatica, breve e in linguaggio semplice,
    del perche' di ogni posizione in classifica.

    Interamente basata sui numeri gia' calcolati sopra (nessuna chiamata LLM
    aggiuntiva, nessun giudizio soggettivo): un verdetto in linguaggio
    naturale sul punteggio finale (che include anche la similarita' di
    *significato* via embedding, non solo le parole condivise), l'accordo
    col triage di gruppo e la privacy. Tenuta volutamente corta: 3-4 frasi
    semplici per modello, non una tabella di numeri travestita da prosa.
    """
    if ranking_df.empty:
        return []

    L = _L(lang)
    n = len(ranking_df)
    majority_label = compare.get("urgency_majority_label")
    majority_text = t(URGENCY_META.get(majority_label, URGENCY_META[None])["label_key"], lang) if majority_label else None

    items = []
    for _, row in ranking_df.iterrows():
        key = row["key"]
        cfg = MODEL_CONFIG.get(key, {})
        rank = int(row[L["rank"]])
        score = row[L["score_final"]]
        bullets = []

        sem = row.get(L["sem_short"])
        sem_clause = t("narrative.sem_clause", lang, sem=sem) if sem is not None else ""
        bullets.append(t(_verdict_key(score), lang, score=score, sem_clause=sem_clause))

        if use_gold and row.get(L["acc_clin_short"]) is not None:
            sem_g = row.get(L["sem_clin_short"])
            sem_g_clause = t("narrative.sem_clause", lang, sem=sem_g) if sem_g is not None else ""
            bullets.append(
                t(
                    "narrative.gold_accuracy",
                    lang,
                    acc=row[L["acc_clin_short"]],
                    cov=row[L["ddx_short"]],
                    sem_clause=sem_g_clause,
                )
            )

        u = compare.get("urgency", {}).get(key, {})
        u_label = u.get("label")
        if u_label and majority_label:
            u_label_text = t(URGENCY_META.get(u_label, URGENCY_META[None])["label_key"], lang)
            if u_label == majority_label:
                bullets.append(t("narrative.urgency_match", lang, label=u_label_text))
            else:
                bullets.append(t("narrative.urgency_diff", lang, label=u_label_text, majority=majority_text))
        elif u_label:
            u_label_text = t(URGENCY_META.get(u_label, URGENCY_META[None])["label_key"], lang)
            bullets.append(t("narrative.urgency_match", lang, label=u_label_text))
        else:
            bullets.append(t("narrative.urgency_none", lang))

        if cfg.get("cloud"):
            bullets.append(t("narrative.privacy_cloud", lang, vendor=cfg.get("vendor", cfg.get("name", ""))))
        else:
            bullets.append(t("narrative.privacy_local", lang))

        if rank == 1:
            bullets.append(t("narrative.top", lang))
        elif rank == n and n > 1:
            bullets.append(t("narrative.bottom", lang))

        items.append(
            {
                "key": key,
                "rank": rank,
                "name": row[L["model"]],
                "icon": cfg.get("icon", "🔹"),
                "color": cfg.get("color", "#94a3b8"),
                "score": row[L["score_final"]],
                "bullets": bullets,
                "tone": "strength" if rank == 1 else ("watch" if rank == n and n > 1 else "neutral"),
            }
        )

    return items


def build_score_explanations(
    compare: dict, model_keys: list, lang: str = "en", use_gold: bool = False
) -> list:
    """Full, numeric "show your work" breakdown for every model and every KPI.

    Feeds the "why this score" detail dialog: for each model, the exact
    pairwise numbers that were averaged into Reliability and Semantic
    similarity, the consensus keywords behind Accuracy, and the literal
    weighted formula that produced the Final score — so nothing about the
    ranking is a black box.
    """
    names = {k: MODEL_CONFIG[k]["name"] for k in model_keys if k in MODEL_CONFIG}
    rel_pairs = compare.get("reliability_pairs", {})
    acc_pairs = compare.get("accuracy_pairs", {})
    sem_pairs = compare.get("semantic_pairs", {})
    sem_available = compare.get("semantic_available", False)
    gold = compare.get("gold") if use_gold else None

    items = []
    for key in model_keys:
        cfg = MODEL_CONFIG.get(key, {})
        if not cfg:
            continue
        rel = compare.get("reliability", {}).get(key, 0.0)
        acc = compare.get("accuracy_consensus", {}).get(key, 0.0)
        sem = compare.get("semantic_similarity", {}).get(key) if sem_available else None
        final_cons = _blend_score(rel, acc, sem)

        rel_detail = [
            {"other": names.get(j, j), "value": v}
            for j, v in (rel_pairs.get(key, {}) or {}).items()
        ]
        acc_detail = [
            {"other": names.get(j, j), "value": v}
            for j, v in (acc_pairs.get(key, {}) or {}).items()
        ]
        sem_detail = [
            {"other": names.get(j, j), "value": v}
            for j, v in (sem_pairs.get(key, {}) or {}).items()
            if v is not None
        ]
        own_primary_kw = sorted(compare.get("primary_keywords", {}).get(key, set()))
        consensus_kw = compare.get("consensus_keywords", [])
        matched_kw = sorted(set(own_primary_kw) & set(consensus_kw))

        entry = {
            "key": key,
            "name": cfg.get("name", key),
            "icon": cfg.get("icon", "🔹"),
            "color": cfg.get("color", "#94a3b8"),
            "cloud": cfg.get("cloud", False),
            "primary_text": compare.get("primary_diagnosis_text", {}).get(key, ""),
            "reliability": {"value": rel, "pairs": rel_detail},
            "accuracy_consensus": {
                "value": acc,
                "pairs": acc_detail,
                "own_keywords": own_primary_kw[:10],
                "consensus_keywords": consensus_kw[:10],
                "matched_keywords": matched_kw,
            },
            "semantic": {"value": sem, "available": sem_available, "pairs": sem_detail},
            "privacy": privacy_score(cfg.get("cloud", False)),
            "consensus_score": final_cons,
            "urgency": compare.get("urgency", {}).get(key, {"label": None, "score": None}),
            "gold": None,
            "final_score": final_cons,
        }

        if gold:
            acc_g = gold["accuracy_primary"].get(key, 0.0)
            cov_g = gold["coverage_ddx"].get(key, 0.0)
            sem_g_available = gold.get("semantic_available", False)
            sem_g = gold.get("semantic_accuracy", {}).get(key) if sem_g_available else None
            score_gold = _blend_score(acc_g, cov_g, sem_g, weights=(0.35, 0.35, 0.3))
            entry["gold"] = {
                "accuracy_primary": acc_g,
                "coverage_ddx": cov_g,
                "semantic": sem_g,
                "semantic_available": sem_g_available,
                "score": score_gold,
                "grade_10": clinical_grade_10(score_gold),
                "gold_keywords": gold.get("gold_keywords", [])[:10],
            }
            entry["final_score"] = round((final_cons + score_gold) / 2, 1)

        items.append(entry)

    items.sort(key=lambda e: e["final_score"], reverse=True)
    return items


def build_leaderboard_df(history: list, lang: str = "en") -> pd.DataFrame:
    """Aggrega la cronologia dei round eseguiti in sessione in una classifica cumulativa."""
    L = _L(lang)
    if not history:
        return pd.DataFrame()

    wins: dict = {}
    totals: dict = {}
    counts: dict = {}
    for entry in history:
        wins[entry["winner_key"]] = wins.get(entry["winner_key"], 0) + 1
        for key, score in entry.get("scores", {}).items():
            totals[key] = totals.get(key, 0.0) + (score or 0.0)
            counts[key] = counts.get(key, 0) + 1

    rows = []
    for key, cfg in MODEL_CONFIG.items():
        if key not in counts:
            continue
        avg_score = round(totals[key] / counts[key], 1) if counts.get(key) else 0.0
        rows.append(
            {
                "key": key,
                L["model"]: cfg["name"],
                t("leaderboard.wins", lang): wins.get(key, 0),
                t("leaderboard.avg_score", lang): avg_score,
                t("leaderboard.rounds", lang): counts[key],
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(
            [t("leaderboard.wins", lang), t("leaderboard.avg_score", lang)],
            ascending=[False, False],
        ).reset_index(drop=True)
    return df
