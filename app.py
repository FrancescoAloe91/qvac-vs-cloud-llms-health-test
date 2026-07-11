"""QVAC vs Cloud LLMs - Health Test — Medical benchmark dashboard."""

import time

import pandas as pd
import streamlit as st

from lib import charts, diagnosis_compare, medpsy, metrics, reset, ui, vlm
from lib.browser import cloud_url, copy_to_clipboard, open_all_cloud_tabs
from lib.cases import CASE_IDS, build_prompt, case_meta, case_text_for, default_case_text
from lib.i18n import DEFAULT_LANG, tier_description, t
from lib.lang_switch import apply_language_switch
from lib.metrics import _L
from lib.tiers import MODEL_CONFIG, TIERS, build_tier_prompt
from lib.wallet import REWARD_DATA_SALE, add_reward, load_wallet

st.set_page_config(
    page_title="QVAC vs Cloud LLMs - Health Test",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

ui.inject_css()

TIER_BADGE = {"light": "tier-light", "medium": "tier-medium", "premium": "tier-premium"}
TIER_ICON = {"light": "⚡", "medium": "⚖️", "premium": "🔬"}
ALL_KEYS = ("chatgpt", "claude", "gemini", "qvac")


def widget_key(model_key: str) -> str:
    return f"out_{model_key}"


def set_output_widget(model_key: str, value: str) -> None:
    st.session_state[widget_key(model_key)] = value


if "lang" not in st.session_state:
    st.session_state.lang = DEFAULT_LANG
if "wallet" not in st.session_state:
    st.session_state.wallet = load_wallet()
for k, v in [
    ("benchmark_results", {}),
    ("user_outputs", {}),
    ("case_text", default_case_text(DEFAULT_LANG)),
    ("case_id", "case1"),
    ("case_text_version", 0),
    ("vlm_extraction", None),
    ("selected_tier", "medium"),
    ("browser_info", None),
    ("use_gold_standard", False),
    ("gold_standard_text", ""),
    ("lang_switch_notice", None),
    ("session_history", []),
    ("sell_step", None),
    ("qvac_thinking", ""),
    ("output_tier", {}),
    ("output_tier_text_cache", {}),
]:
    if k not in st.session_state:
        st.session_state[k] = v

lang = st.session_state.lang


def effective_outputs() -> dict:
    out = {}
    results = st.session_state.benchmark_results
    for key in ALL_KEYS:
        wk = widget_key(key)
        edited = st.session_state.get(wk, st.session_state.user_outputs.get(key, "")).strip()
        if edited:
            out[key] = edited
        elif key in results:
            out[key] = results[key].get("content", "")
        else:
            out[key] = ""
    return out


def _load_case(case_id: str) -> None:
    st.session_state.case_id = case_id
    st.session_state.case_text = case_text_for(case_id, lang)
    st.session_state.case_text_version += 1
    st.session_state.benchmark_results = {}
    st.session_state.user_outputs = {}
    st.session_state.output_tier = {}
    st.session_state.output_tier_text_cache = {}
    for key in ALL_KEYS:
        if widget_key(key) in st.session_state:
            del st.session_state[widget_key(key)]


# =====================================================================
# Dialogs (defined after `lang` so titles are translated on every rerun)
# =====================================================================


@st.dialog(t("onboarding.title", lang), width="large")
def onboarding_dialog():
    steps = [
        ("onboarding.step1_title", "onboarding.step1_body"),
        ("onboarding.step2_title", "onboarding.step2_body"),
        ("onboarding.step3_title", "onboarding.step3_body"),
        ("onboarding.step4_title", "onboarding.step4_body"),
    ]
    for title_key, body_key in steps:
        st.markdown(f"**{t(title_key, lang)}**")
        st.caption(t(body_key, lang))
    st.divider()
    if st.button(t("onboarding.cta", lang), type="primary", use_container_width=True):
        st.rerun()


@st.dialog(t("reset.confirm_title", lang))
def reset_confirm_dialog():
    st.warning(t("reset.confirm_body", lang))
    c1, c2 = st.columns(2)
    with c1:
        if st.button(t("reset.confirm_cancel", lang), use_container_width=True):
            st.rerun()
    with c2:
        if st.button(t("reset.confirm_yes", lang), type="primary", use_container_width=True):
            reset.reset_session()
            st.rerun()


@st.dialog(t("card.full_dialog_title", lang), width="large")
def full_response_dialog(model_key: str):
    cfg = MODEL_CONFIG[model_key]
    text = st.session_state.get(widget_key(model_key), "").strip()
    st.markdown(f"### {cfg['icon']} {cfg['name']}")
    if text:
        st.markdown(text)
        if model_key == "qvac" and st.session_state.get("qvac_thinking"):
            with st.expander("🧠 " + t("card.reasoning_expander", lang)):
                st.caption(t("card.reasoning_caption", lang))
                st.markdown(
                    f'<div class="qvac-live-stream" style="max-height:320px;">'
                    f'{st.session_state.qvac_thinking}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info(t("card.status_empty", lang))


@st.dialog(t("explain.dialog_title", lang), width="large")
def explain_scores_dialog(explanations: list, use_gold: bool):
    st.caption(t("explain.dialog_intro", lang))
    if not explanations:
        st.info(t("warn.no_output", lang))
        return

    model_tabs = st.tabs([f"{e['icon']} {e['name']}" for e in explanations])
    for tab, e in zip(model_tabs, explanations):
        with tab:
            st.markdown(
                f"#### {e['icon']} {e['name']} — "
                f"{t('cols.final_score', lang)}: **{e['final_score']}%**"
            )

            st.markdown(f"**{t('explain.reliability_label', lang)}**")
            st.caption(t("explain.reliability_desc", lang))
            rel = e["reliability"]
            st.metric(t("cols.reliability_short", lang), f"{rel['value']}%")
            if rel["pairs"]:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                t("explain.select_model", lang): t("explain.vs", lang, name=p["other"]),
                                t("cols.reliability_short", lang): f"{p['value']}%",
                            }
                            for p in rel["pairs"]
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown(f"**{t('explain.accuracy_label', lang)}**")
            st.caption(t("explain.accuracy_desc", lang))
            acc = e["accuracy_consensus"]
            st.metric(t("cols.accuracy_consensus_short", lang), f"{acc['value']}%")
            if acc["pairs"]:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                t("explain.select_model", lang): t("explain.vs", lang, name=p["other"]),
                                t("cols.accuracy_consensus_short", lang): f"{p['value']}%",
                            }
                            for p in acc["pairs"]
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            st.caption(t("explain.own_keywords", lang))
            st.write(", ".join(acc["own_keywords"]) or t("explain.no_keywords", lang))

            st.markdown(f"**{t('explain.semantic_label', lang)}**")
            st.caption(t("explain.semantic_desc", lang))
            sem = e["semantic"]
            if sem["available"] and sem["value"] is not None:
                st.metric(t("cols.semantic_short", lang), f"{sem['value']}%")
                if sem["pairs"]:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    t("explain.select_model", lang): t("explain.vs", lang, name=p["other"]),
                                    t("cols.semantic_short", lang): f"{p['value']}%",
                                }
                                for p in sem["pairs"]
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.caption(t("explain.semantic_unavailable_note", lang))

            st.markdown(f"**{t('explain.formula_label', lang)}**")
            if sem["available"] and sem["value"] is not None:
                st.code(
                    t(
                        "explain.formula_consensus_3", lang,
                        score=e["consensus_score"], rel=rel["value"], acc=acc["value"], sem=sem["value"],
                    ),
                    language=None,
                )
            else:
                st.code(
                    t("explain.formula_consensus_2", lang, score=e["consensus_score"], rel=rel["value"], acc=acc["value"]),
                    language=None,
                )

            if use_gold and e.get("gold"):
                g = e["gold"]
                st.divider()
                st.markdown(f"**{t('explain.gold_label', lang)}**")
                st.caption(t("explain.gold_desc", lang))
                gcol1, gcol2, gcol3 = st.columns(3)
                gcol1.metric(t("cols.primary_accuracy", lang), f"{g['accuracy_primary']}%")
                gcol2.metric(t("cols.ddx_coverage", lang), f"{g['coverage_ddx']}%")
                if g["semantic_available"] and g["semantic"] is not None:
                    gcol3.metric(t("cols.semantic_gold_short", lang), f"{g['semantic']}%")
                st.metric(f"🎓 {t('explain.grade_label', lang)}", f"{g['grade_10']} / 10")
                st.caption(t("explain.grade_rubric", lang))
                st.code(
                    t("explain.formula_final_gold", lang, final=e["final_score"], cons=e["consensus_score"], gold=g["score"]),
                    language=None,
                )

            u = e.get("urgency", {})
            st.divider()
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                st.caption(t("explain.urgency_label", lang))
                st.write(u.get("label") or "—")
            with fcol2:
                st.caption(t("explain.privacy_label", lang))
                st.write(f"{e['privacy']}%")


@st.dialog(t("decision.cloud_dialog_title", lang))
def cloud_decision_dialog():
    st.error(t("decision.cloud_dialog_body", lang))
    if st.button(t("decision.close", lang), use_container_width=True):
        st.rerun()


@st.dialog(t("decision.qvac_dialog_title", lang))
def qvac_decision_dialog():
    st.success(t("decision.qvac_dialog_body", lang))
    if st.button(t("decision.close", lang), use_container_width=True):
        st.rerun()


@st.dialog(t("decision.sell_dialog_title", lang))
def sell_decision_dialog():
    step = st.session_state.get("sell_step")

    if step == "success":
        st.markdown(
            ui.reward_success_html(
                f"{REWARD_DATA_SALE:.2f} USDT",
                t("decision.sell_new_balance", lang),
                f"{st.session_state.wallet['balance']:.2f} USDT",
            ),
            unsafe_allow_html=True,
        )
        st.success(f"✅ {t('decision.sell_success_title', lang)} — {t('decision.sell_success_body', lang, amount=REWARD_DATA_SALE)}")
        if st.button(t("decision.close", lang), type="primary", use_container_width=True):
            st.session_state.sell_step = None
            st.rerun()
        return

    st.info(t("decision.sell_dialog_body", lang))
    st.markdown(f"**{t('decision.sell_question', lang, amount=REWARD_DATA_SALE)}**")
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button(t("decision.sell_cancel", lang), use_container_width=True):
            st.session_state.sell_step = None
            st.rerun()
    with cc2:
        if st.button(
            t("decision.sell_confirm", lang, amount=REWARD_DATA_SALE),
            type="primary",
            use_container_width=True,
        ):
            st.session_state.wallet = add_reward(st.session_state.wallet, REWARD_DATA_SALE, "Research")
            st.session_state.sell_step = "success"
            st.balloons()
            st.rerun()


# --- Sidebar (all controls stay docked here, left column) ---
with st.sidebar:
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:7px; margin-bottom:0.5rem;">'
        f'<div style="font-size:1.15rem; width:28px; height:28px; border-radius:8px; '
        f'background:rgba(0,208,156,0.14); display:flex; align-items:center; justify-content:center;">🩺</div>'
        f'<div style="font-weight:800; font-size:0.88rem; line-height:1.15;">QVAC<br/>Health Test</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.button(t("sidebar.guide_btn", lang), use_container_width=True, type="primary"):
        onboarding_dialog()

    if st.button(
        f"🔄 {t('sidebar.reset', lang)}",
        use_container_width=True,
        help=t("sidebar.reset_help", lang),
    ):
        reset_confirm_dialog()

    st.metric("💰 " + t("sidebar.wallet", lang), f"{st.session_state.wallet['balance']:.2f} USDT")

    with st.expander("👁️ " + t("sidebar.vlm", lang), expanded=False):
        uploaded = st.file_uploader(t("sidebar.vlm_upload", lang), type=["jpg", "jpeg", "png", "pdf"])
        if uploaded:
            st.success(t("vlm.ready", lang))
            if st.button(t("sidebar.vlm_extract", lang), use_container_width=True):
                st.session_state.vlm_extraction = vlm.extract_text(
                    uploaded.name, uploaded.getvalue(), lang
                )
            if st.session_state.vlm_extraction and st.button(
                t("sidebar.vlm_add", lang), use_container_width=True
            ):
                from lib.cases import VLM_MARKERS

                st.session_state.case_text += (
                    f"\n\n{VLM_MARKERS[lang]}\n{st.session_state.vlm_extraction}"
                )
                st.session_state.case_id = None
                st.session_state.case_text_version += 1
                st.rerun()

    st.caption("🔒 100% on-device inference for QVAC MedPsy · cloud models require manual copy/paste.")

# --- Header ---
hdr_l, hdr_r = st.columns([5, 1.3])
with hdr_l:
    st.markdown(f'<p class="app-title fade-in">🩺 {t("title", lang)}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="app-subtitle">{t("subtitle", lang)}</p>', unsafe_allow_html=True)
    st.markdown(
        ui.live_chip_html("QVAC MedPsy 4B · on-device")
        + "&nbsp;&nbsp;"
        + ui.live_chip_html(f"{st.session_state.wallet['balance']:.2f} USDT"),
        unsafe_allow_html=True,
    )
with hdr_r:
    lc1, lc2 = st.columns(2)
    with lc1:
        if st.button("🇬🇧 EN", use_container_width=True, type="primary" if lang == "en" else "secondary"):
            if lang != "en":
                apply_language_switch(lang, "en")
                st.session_state.lang = "en"
                st.rerun()
    with lc2:
        if st.button("🇮🇹 IT", use_container_width=True, type="primary" if lang == "it" else "secondary"):
            if lang != "it":
                apply_language_switch(lang, "it")
                st.session_state.lang = "it"
                st.rerun()

if st.session_state.lang_switch_notice:
    st.info(st.session_state.lang_switch_notice)

# --- Compact progress stepper (replaces bulky numbered section headers) ---
_run_done = bool(st.session_state.benchmark_results)
_any_pasted = any(
    (st.session_state.get(widget_key(k), "") or st.session_state.user_outputs.get(k, "")).strip()
    for k in ALL_KEYS
)
st.markdown(
    ui.stepper_html(
        [
            (t("stepper.case", lang), "done"),
            (t("stepper.tier", lang), "done" if _run_done else "current"),
            (t("stepper.run", lang), "done" if _run_done else "current"),
            (t("stepper.results", lang), "done" if _any_pasted else ("current" if _run_done else "todo")),
        ]
    ),
    unsafe_allow_html=True,
)

# =====================================================================
# 1) Case picker — compact segmented control + info bar (was 5 big cards)
# =====================================================================
st.markdown(ui.eyebrow_html("🗂️", t("eyebrow.case", lang)), unsafe_allow_html=True)

pick_col, prev_col = st.columns([6, 1])
with pick_col:
    _case_labels = {
        cid: f"{case_meta(cid)['icon']} {t(f'case.short.{cid}', lang)}" for cid in CASE_IDS
    }
    picked_case = st.segmented_control(
        t("case.picker_label", lang),
        options=CASE_IDS,
        format_func=lambda cid: _case_labels[cid],
        default=st.session_state.case_id if st.session_state.case_id in CASE_IDS else None,
        key=f"case_seg_{st.session_state.case_id or 'custom'}",
        label_visibility="collapsed",
    )
with prev_col:
    with st.popover("👁️", use_container_width=True, help=t("case.preview_btn", lang)):
        _preview_id = st.session_state.case_id or "case1"
        _pm = case_meta(_preview_id)
        st.markdown(f"**{_pm['icon']} {t(f'cases.{_preview_id}', lang)}**")
        st.caption(f"🎯 {t(_pm['focus_key'], lang)}")
        st.markdown(case_text_for(_preview_id, lang))

if picked_case and picked_case != st.session_state.case_id:
    _load_case(picked_case)
    st.rerun()

if st.session_state.case_id:
    _am = case_meta(st.session_state.case_id)
    st.markdown(
        ui.case_info_bar_html(
            _am["icon"],
            _am["color"],
            t(_am["specialty_key"], lang),
            t(f"cases.{st.session_state.case_id}", lang),
            t("case.focus_label", lang),
            t(_am["focus_key"], lang),
        ),
        unsafe_allow_html=True,
    )
else:
    st.caption("✏️ " + t("case.custom_hint", lang))

with st.expander("📝 " + t("case.clinical", lang), expanded=(st.session_state.case_id is None)):
    case_text = st.text_area(
        t("case.clinical", lang),
        value=st.session_state.case_text,
        height=100,
        key=f"case_editor_v{st.session_state.case_text_version}",
        label_visibility="collapsed",
    )
    if case_text != st.session_state.case_text:
        st.session_state.case_text = case_text
        st.session_state.case_id = None

full_prompt = build_prompt(st.session_state.case_text, lang)

# =====================================================================
# 2) Tier + Run — merged into one compact row (was 2 separate sections)
# =====================================================================
st.markdown(ui.eyebrow_html("⚙️", t("eyebrow.tier", lang)), unsafe_allow_html=True)

TIER_KEYS = ["light", "medium", "premium"]
ctrl1, ctrl2, ctrl3 = st.columns([3, 1.3, 2.1])
with ctrl1:
    tier_pick = st.segmented_control(
        t("tier.radio", lang),
        options=TIER_KEYS,
        format_func=lambda tk: f"{TIER_ICON[tk]} {TIERS[tk].label}",
        default=st.session_state.selected_tier,
        key="tier_segmented",
        label_visibility="collapsed",
    )
    tier_choice = tier_pick or st.session_state.selected_tier
with ctrl2:
    run_benchmark = st.button("🚀 " + t("benchmark.run", lang), type="primary", use_container_width=True)
with ctrl3:
    open_browser = st.checkbox(t("browser.open", lang), value=False, help=t("browser.help", lang))

st.session_state.selected_tier = tier_choice
st.markdown(
    f'<div class="glass-panel fade-in"><span class="{TIER_BADGE[tier_choice]}">{TIERS[tier_choice].label}</span> '
    f'<span style="color:#cbd5e1; font-size:0.8rem;">{tier_description(tier_choice, lang)}</span> '
    f'<span style="color:#64748b; font-size:0.72rem; font-style:italic;">— {t("tier.qvac_only_tag", lang)}</span></div>',
    unsafe_allow_html=True,
)

tiered_prompt = build_tier_prompt(full_prompt, tier_choice, lang)

# The tier/depth selector is a QVAC-only knob (see caption below): the text
# copied for the cloud sites is always the plain, untiered prompt, identical
# no matter which depth is selected — that is what keeps the comparison fair.
with st.expander(t("prompt.expander", lang), expanded=False):
    st.code(full_prompt, language="text")
    if st.button("📋 " + t("prompt.copy", lang)):
        if copy_to_clipboard(full_prompt):
            st.success(t("prompt.copied", lang))

st.caption(t("caption.cloud", lang))

if run_benchmark:
    if open_browser:
        st.session_state.browser_info = open_all_cloud_tabs(lang)
    else:
        st.session_state.browser_info = None

    qvac = None
    if not medpsy.ollama_available():
        st.error(t("error.ollama_offline", lang))
    elif not medpsy.model_ready():
        st.error(t("error.model_missing", lang))
    else:
        with st.status(t("status.step_loading", lang), expanded=True) as status:
            status.update(label=t("status.step_generating", lang))
            stream_box = st.empty()
            partial_text = ""
            result = None
            t0 = time.time()
            for event in medpsy.stream_inference(tiered_prompt, tier_choice):
                if event.get("delta"):
                    partial_text += event["delta"]
                    elapsed = time.time() - t0
                    preview = partial_text[-1800:]
                    stream_box.markdown(
                        f'<div class="qvac-live-stream">{preview}▌</div>'
                        f'<div class="qvac-live-meta">⏱ {elapsed:.0f}s · '
                        f'{t("status.live_tokens", lang, n=len(partial_text.split()))}</div>',
                        unsafe_allow_html=True,
                    )
                if event.get("done"):
                    result = event
            stream_box.empty()

            if not result or result.get("error"):
                status.update(label=t("status.step_error", lang), state="error")
                st.error(t("error.ollama_runtime", lang, error=(result or {}).get("error", "unknown")))
            else:
                status.update(label=t("status.step_done", lang), state="complete")
                qvac = result

    if qvac:
        qvac.update(model_key="qvac", name=MODEL_CONFIG["qvac"]["name"], tier="local")
        content = qvac.get("content", "")
        st.session_state.benchmark_results = {"qvac": qvac}
        set_output_widget("qvac", content)
        st.session_state.user_outputs["qvac"] = content
        st.session_state.output_tier["qvac"] = tier_choice
        st.session_state.output_tier_text_cache["qvac"] = content.strip()
        st.session_state.qvac_thinking = qvac.get("thinking", "")
        # Deliberately do NOT touch chatgpt/claude/gemini here: running (or
        # re-running) QVAC must never erase what the user already pasted from
        # the cloud sites for this same clinical case.

if st.session_state.browser_info:
    info = st.session_state.browser_info
    st.success(f"✅ {t('browser.opened', lang)}: {', '.join(info['opened'])}")
    st.caption(info.get("note", ""))

# --- Gold standard (compact) ---
with st.expander("🎯 " + t("gold.section", lang), expanded=st.session_state.use_gold_standard):
    use_gold = st.checkbox(
        t("gold.use", lang),
        value=st.session_state.use_gold_standard,
        help=t("gold.help", lang),
    )
    st.session_state.use_gold_standard = use_gold
    if use_gold:
        st.caption(t("gold.caption", lang))
        gold_text = st.text_area(
            t("gold.input", lang),
            value=st.session_state.gold_standard_text,
            height=70,
            placeholder=t("gold.placeholder", lang),
            key="gold_standard_input",
            label_visibility="collapsed",
        )
        st.session_state.gold_standard_text = gold_text
    else:
        st.session_state.gold_standard_text = ""

# =====================================================================
# 4) Model output cards
# =====================================================================
st.markdown(ui.eyebrow_html("💬", t("eyebrow.output", lang)), unsafe_allow_html=True)
results = st.session_state.benchmark_results
c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

for col, key in zip([c1, c2, c3, c4], ALL_KEYS):
    cfg = MODEL_CONFIG[key]

    with col:
        wk = widget_key(key)
        if wk not in st.session_state:
            initial = st.session_state.user_outputs.get(key, "")
            if not initial and key in results:
                initial = results[key].get("content", "")
            st.session_state[wk] = initial

        current_text = st.session_state.get(wk, "").strip()

        # The depth selector is a QVAC-only knob (cloud sites always get the
        # same plain prompt — see caption above), so only QVAC's card needs a
        # depth badge, tracked against what actually produced its current
        # text. Cloud cards show no tier badge at all: showing one there would
        # imply the selector changed their prompt, which it never does.
        tier_mismatch = False
        if cfg["cloud"]:
            badge_html = ""
        else:
            if current_text:
                if st.session_state.output_tier_text_cache.get(key) != current_text:
                    st.session_state.output_tier[key] = tier_choice
                    st.session_state.output_tier_text_cache[key] = current_text
            else:
                st.session_state.output_tier.pop(key, None)
                st.session_state.output_tier_text_cache.pop(key, None)

            recorded_tier = st.session_state.output_tier.get(key, tier_choice)
            tier_mismatch = bool(current_text) and recorded_tier != tier_choice
            badge_html = f'<span class="{TIER_BADGE.get(recorded_tier, "tier-local")}">{TIERS[recorded_tier].label}</span>'

        word_count = len(current_text.split()) if current_text else 0
        status_html = (
            f'<span class="status-pill status-filled">{t("card.status_filled", lang, n=word_count)}</span>'
            if current_text
            else f'<span class="status-pill status-empty">{t("card.status_empty", lang)}</span>'
        )

        link_html = (
            f'<a class="card-link-pill" href="{cloud_url(key, lang)}" target="_blank" rel="noopener">'
            f'{t("output.link", lang)}</a>'
            if cfg["cloud"] and cfg.get("url")
            else ""
        )
        st.markdown(
            f'<div class="model-card fade-in" style="--model-color:{cfg["color"]};">'
            f'<div class="model-card-head">'
            f'<span class="model-card-name"><span class="m-icon">{cfg["icon"]}</span>{cfg["name"]} '
            f'{badge_html}{link_html}</span>{status_html}</div>'
            f'<div class="model-vendor">{cfg["vendor"]}</div>'
            f'<div class="model-instructions">'
            f'{t("card.instructions_cloud", lang, name=cfg["name"]) if cfg["cloud"] else t("card.instructions_local", lang)}'
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if tier_mismatch:
            st.caption(
                "⚠️ "
                + t(
                    "card.tier_mismatch",
                    lang,
                    old=TIERS[recorded_tier].label,
                    new=TIERS[tier_choice].label,
                )
            )

        placeholder = (
            t("output.placeholder_cloud", lang)
            if cfg["cloud"]
            else t("output.placeholder_qvac", lang)
        )
        st.text_area(
            t("output.diagnosis", lang),
            height=160,
            placeholder=placeholder,
            key=wk,
            label_visibility="collapsed",
        )
        st.session_state.user_outputs[key] = st.session_state[wk]

        fbtn1, fbtn2 = st.columns([2, 1])
        with fbtn1:
            if key == "qvac" and key in results:
                stats = results[key].get("stats", {})
                if stats:
                    st.caption(
                        t(
                            "output.stats",
                            lang,
                            ttft=stats.get("ttft_s") or "—",
                            tps=stats.get("tps") or "—",
                            latency=stats.get("latency_s") or "—",
                            ram=stats.get("ram_gb") or "—",
                        )
                    )
        with fbtn2:
            if st.button(t("card.view_full", lang), key=f"view_{key}", use_container_width=True, disabled=not current_text):
                full_response_dialog(key)

st.button("🔄 " + t("recalc", lang), key="recalc_btn", use_container_width=True)

outputs = effective_outputs()
has_any_output = any(v.strip() for v in outputs.values())
L = _L(lang)

if not has_any_output:
    st.warning(t("warn.no_output", lang))
else:
    compare_input = {
        k: {"output": outputs[k], "name": MODEL_CONFIG[k]["name"]}
        for k in ALL_KEYS
        if outputs[k].strip()
    }

    if compare_input:
        gold_ref = (
            st.session_state.gold_standard_text.strip()
            if st.session_state.use_gold_standard
            else None
        )
        compare = diagnosis_compare.compare_all(compare_input, gold_standard_text=gold_ref)
        model_keys = list(compare_input.keys())
        use_gold_cmp = compare.get("mode") == "gold_standard"
        ranking_df = metrics.build_unified_ranking(compare, model_keys, lang)

        # -------------------------------------------------------------
        # KPI command center — always visible, side by side
        # -------------------------------------------------------------
        st.markdown(ui.eyebrow_html("📌", t("eyebrow.results", lang)), unsafe_allow_html=True)

        privacy_vals = [metrics.privacy_score(MODEL_CONFIG[k]["cloud"]) for k in model_keys]
        privacy_avg = round(sum(privacy_vals) / len(privacy_vals), 1) if privacy_vals else 0.0
        consensus_vals = list(compare.get("accuracy_consensus", {}).values()) + list(
            compare.get("reliability", {}).values()
        )
        if compare.get("semantic_available"):
            consensus_vals += [v for v in compare.get("semantic_similarity", {}).values() if v is not None]
        consensus_avg = round(sum(consensus_vals) / len(consensus_vals), 1) if consensus_vals else 0.0
        qvac_latency = results.get("qvac", {}).get("stats", {}).get("latency_s")
        time_saved = metrics.time_saved_seconds(qvac_latency) if qvac_latency else None
        best_row = ranking_df.iloc[0] if not ranking_df.empty else None

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            best_html = (
                f'{MODEL_CONFIG[best_row["key"]]["icon"]} {best_row[L["model"]]}'
                if best_row is not None
                else "—"
            )
            st.markdown(
                ui.kpi_tile_html(t("kpi.best_model", lang), best_html, accent=True, delay=1),
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                ui.kpi_tile_html(
                    t("kpi.privacy_avg", lang), f"{privacy_avg:.0f}%",
                    sub=t("kpi.privacy_avg_help", lang), delay=2,
                ),
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                ui.kpi_tile_html(
                    t("kpi.consensus_avg", lang), f"{consensus_avg:.0f}%",
                    sub=t("kpi.consensus_avg_help", lang), delay=3,
                ),
                unsafe_allow_html=True,
            )
        with k4:
            tri_agree = compare.get("urgency_agreement", 0.0)
            st.markdown(
                ui.kpi_tile_html(
                    t("kpi.triage_agreement", lang), f"{tri_agree:.0f}%",
                    sub=t("kpi.triage_agreement_help", lang), delay=4,
                ),
                unsafe_allow_html=True,
            )
        with k5:
            ts_val = f"{time_saved:.0f}s" if time_saved is not None else "—"
            st.markdown(
                ui.kpi_tile_html(
                    t("kpi.time_saved", lang),
                    ts_val,
                    sub=t("kpi.time_saved_help", lang, overhead=metrics.CLOUD_MANUAL_OVERHEAD_S),
                    delay=5,
                ),
                unsafe_allow_html=True,
            )

        # -------------------------------------------------------------
        # Ranking hero — order, chart and score immediately visible,
        # right under the KPI tiles, with a written "why" underneath.
        # Since TPS/TTFT can't be measured on cloud sites without an API,
        # this is deliberately centered on real diagnostic content instead.
        # -------------------------------------------------------------
        st.markdown(ui.eyebrow_html("🏆", t("ranking.section", lang)), unsafe_allow_html=True)
        if not ranking_df.empty:
            # Compact charts side by side (ranking bars + privacy), then the
            # FULL table with every column underneath at full width, sized to
            # show every row with no internal scrollbar.
            rk_col1, rk_col2 = st.columns([1, 1])
            with rk_col1:
                st.plotly_chart(
                    charts.fig_ranking_bars(ranking_df, use_gold_cmp, lang, height=260),
                    use_container_width=True,
                    key="chart_ranking_hero",
                )
            with rk_col2:
                st.plotly_chart(
                    charts.fig_privacy_gauges(ranking_df, lang, height=260),
                    use_container_width=True,
                    key="chart_privacy_hero",
                )

            consensus_df = metrics.build_consensus_table(compare, tier_choice, model_keys, lang)
            st.dataframe(
                consensus_df,
                use_container_width=True,
                hide_index=True,
                height=ui.table_height(len(consensus_df)),
            )
            st.caption(t("ranking.legend", lang))
            if not compare.get("semantic_available"):
                st.caption(t("kpi.semantic_unavailable", lang))

            narrative_items = metrics.build_ranking_narrative(ranking_df, compare, model_keys, lang, use_gold_cmp)
            if narrative_items:
                st.markdown(ui.eyebrow_html("📝", t("narrative.section", lang)), unsafe_allow_html=True)
                st.caption(t("narrative.section_caption", lang))
                nc1, nc2 = st.columns(2)
                for i, item in enumerate(narrative_items):
                    with (nc1 if i % 2 == 0 else nc2):
                        st.markdown(
                            ui.narrative_card_html(
                                item["rank"], item["icon"], item["color"], item["name"],
                                item["score"], item["bullets"], item["tone"],
                            ),
                            unsafe_allow_html=True,
                        )
        else:
            st.info(t("warn.no_output", lang))

        # -------------------------------------------------------------
        # Full KPI breakdown — always visible, no tab clicks: same data as
        # the table above, plus the mode explanation, gold-standard table
        # (if any), supporting metrics and the full "why" dialog trigger.
        # -------------------------------------------------------------
        st.markdown(ui.eyebrow_html("📊", t("kpi.glance_title", lang)), unsafe_allow_html=True)
        st.caption(t("kpi.glance_caption", lang))
        if use_gold_cmp:
            st.info(t("kpi.mode_note_gold", lang))
        else:
            st.info(t("kpi.mode_note_consensus", lang))

        if use_gold_cmp:
            st.markdown("#### " + t("kpi.gold_section", lang))
            st.caption(t("kpi.gold_caption", lang))
            gold_df = metrics.build_gold_table(compare, tier_choice, model_keys, lang)
            st.dataframe(
                gold_df, use_container_width=True, hide_index=True, height=ui.table_height(len(gold_df))
            )
            if compare.get("gold", {}).get("gold_diagnoses"):
                with st.expander(t("kpi.gold_diagnoses", lang)):
                    for i, d in enumerate(compare["gold"]["gold_diagnoses"], 1):
                        st.markdown(f"{i}. {d}")

        gc1, gc2, gc3 = st.columns(3)
        gc1.metric(t("kpi.primary_agreement", lang), f"{compare['primary_agreement']}%")
        gc2.metric(t("kpi.qvac_cloud", lang), f"{compare.get('qvac_cloud_concordance', 0)}%")
        gc3.metric(t("kpi.models_compared", lang), compare["active_count"])
        if compare.get("consensus_keywords"):
            st.caption(
                t("kpi.consensus_keywords", lang) + ": "
                + ", ".join(compare["consensus_keywords"][:12])
            )
        if compare["matrix"]:
            with st.expander(t("kpi.matrix_expander", lang)):
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                t("matrix.pair", lang): k,
                                t("matrix.concordance", lang): v,
                            }
                            for k, v in compare["matrix"].items()
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        if st.button(t("kpi.explain_button", lang), use_container_width=True, key="btn_explain_scores"):
            explanations = metrics.build_score_explanations(compare, model_keys, lang, use_gold_cmp)
            explain_scores_dialog(explanations, use_gold_cmp)

        tab_perf, tab_triage, tab_charts, tab_session = st.tabs(
            [
                "⚡ " + t("kpi.performance", lang),
                "🚦 " + t("kpi.triage", lang),
                "📊 " + t("charts.section", lang),
                "📈 " + t("kpi.session", lang),
            ]
        )

        with tab_perf:
            st.caption(t("kpi.performance_caption", lang))
            perf_df = metrics.build_performance_table(results, tier_choice, lang)
            st.dataframe(
                perf_df,
                use_container_width=True,
                hide_index=True,
                height=ui.table_height(len(perf_df)),
            )

        with tab_triage:
            st.caption(t("kpi.triage_caption", lang))
            urgency_df = metrics.build_urgency_table(compare, model_keys, lang)
            st.dataframe(
                urgency_df, use_container_width=True, hide_index=True, height=ui.table_height(len(urgency_df))
            )
            st.metric(t("kpi.triage_agreement", lang), f"{compare.get('urgency_agreement', 0.0)}%")
            st.plotly_chart(
                charts.fig_urgency_compare(compare.get("urgency", {}), lang),
                use_container_width=True,
                key="chart_urgency_tab",
            )

        with tab_charts:
            if not ranking_df.empty:
                st.caption(t("charts.dims_privacy_note", lang))
                (
                    chart_tab_radar,
                    chart_tab_bars,
                    chart_tab_heatmap,
                    chart_tab_keywords,
                    chart_tab_urgency,
                ) = st.tabs(
                    [
                        t("charts.tab_radar", lang),
                        t("charts.tab_bars", lang),
                        t("charts.tab_heatmap", lang),
                        t("charts.tab_keywords", lang),
                        t("charts.tab_urgency", lang),
                    ]
                )
                with chart_tab_radar:
                    st.plotly_chart(
                        charts.fig_radar(
                            ranking_df, use_gold_cmp, lang, sem_available=compare.get("semantic_available", False)
                        ),
                        use_container_width=True,
                        key="chart_radar",
                    )
                with chart_tab_bars:
                    st.plotly_chart(
                        charts.fig_ranking_bars(ranking_df, use_gold_cmp, lang),
                        use_container_width=True,
                        key="chart_bars",
                    )
                with chart_tab_heatmap:
                    if len(model_keys) >= 2:
                        st.plotly_chart(
                            charts.fig_concordance_heatmap(compare.get("matrix_keyed", {}), model_keys, lang),
                            use_container_width=True,
                            key="chart_heatmap",
                        )
                    else:
                        st.info(t("warn.no_output", lang))
                with chart_tab_keywords:
                    kw_counts = compare.get("consensus_keyword_counts", {})
                    if kw_counts:
                        st.plotly_chart(
                            charts.fig_keyword_bar(kw_counts, len(model_keys), lang),
                            use_container_width=True,
                            key="chart_keywords",
                        )
                    else:
                        st.info(t("warn.no_output", lang))
                with chart_tab_urgency:
                    st.plotly_chart(
                        charts.fig_urgency_compare(compare.get("urgency", {}), lang),
                        use_container_width=True,
                        key="chart_urgency_sub",
                    )
            else:
                st.info(t("warn.no_output", lang))

        with tab_session:
            st.caption(t("leaderboard.caption", lang))
            case_label = (
                t(f"cases.{st.session_state.case_id}", lang)
                if st.session_state.case_id
                else t("case.specialty.custom", lang)
            )
            add_col, clear_col = st.columns([3, 1])
            with add_col:
                if st.button("➕ " + t("leaderboard.add_round", lang), use_container_width=True, disabled=ranking_df.empty):
                    entry = metrics.build_session_entry(
                        case_label, TIERS[tier_choice].label, ranking_df, compare, lang
                    )
                    if entry:
                        st.session_state.session_history.append(entry)
                        st.toast(t("leaderboard.added_toast", lang), icon="📈")
            with clear_col:
                if st.button(t("leaderboard.clear", lang), use_container_width=True, disabled=not st.session_state.session_history):
                    st.session_state.session_history = []
                    st.rerun()

            history = st.session_state.session_history
            if not history:
                st.info(t("leaderboard.empty", lang))
            else:
                lb_df = metrics.build_leaderboard_df(history, lang)
                st.plotly_chart(charts.fig_leaderboard(lb_df, lang), use_container_width=True, key="chart_leaderboard")
                st.dataframe(
                    lb_df.drop(columns=["key"]) if "key" in lb_df.columns else lb_df,
                    use_container_width=True,
                    hide_index=True,
                )
                with st.expander(t("leaderboard.history_expander", lang)):
                    for i, entry in enumerate(history, 1):
                        st.markdown(
                            f"**{i}. {entry['case']}** · {entry['tier']} → "
                            f"🏆 {entry['winner_name']} ({entry['winner_score']}%)"
                        )

        st.markdown(ui.eyebrow_html("🪙", t("decision.section", lang)), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f'<p class="decision-lead fade-in">{t("decision.lead", lang)}</p>',
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("🔴 " + t("decision.cloud", lang), use_container_width=True):
                    cloud_decision_dialog()
                st.markdown(
                    f'<p class="decision-caption">{t("decision.cloud_caption", lang)}</p>',
                    unsafe_allow_html=True,
                )
            with b2:
                if st.button("🟢 " + t("decision.qvac", lang), use_container_width=True):
                    qvac_decision_dialog()
                st.markdown(
                    f'<p class="decision-caption">{t("decision.qvac_caption", lang)}</p>',
                    unsafe_allow_html=True,
                )
            with b3:
                if st.button("💠 " + t("decision.sell", lang), use_container_width=True):
                    st.session_state.sell_step = "confirm"
                st.markdown(
                    f'<p class="decision-caption">{t("decision.sell_caption", lang)}</p>',
                    unsafe_allow_html=True,
                )

        if st.session_state.get("sell_step"):
            sell_decision_dialog()

st.markdown(
    '<div class="footer-note">🩺 QVAC vs Cloud LLMs · Demonstration benchmark only — not a substitute for medical advice.</div>',
    unsafe_allow_html=True,
)
