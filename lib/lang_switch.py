"""Translate session content when the UI language changes."""

import streamlit as st

from lib.cases import (
    VLM_MARKERS,
    case_text_for,
    split_vlm_suffix,
    translate_case_text,
)
from lib.i18n import t
from lib.vlm import placeholder_extraction


def _invalidate_qvac() -> None:
    """QVAC's answer is real, measured local inference tied to the exact
    prompt it ran on - it is not translatable by swapping text. On a
    language change we clear it (like the cloud boxes effectively go
    stale too) so the user re-runs the benchmark for a genuine answer
    in the new language, instead of ever showing a fabricated one."""
    if not st.session_state.user_outputs.get("qvac") and "qvac" not in st.session_state.benchmark_results:
        return
    st.session_state.benchmark_results.pop("qvac", None)
    st.session_state.user_outputs["qvac"] = ""
    if "out_qvac" in st.session_state:
        st.session_state["out_qvac"] = ""


def apply_language_switch(old_lang: str, new_lang: str) -> None:
    """Swap preset cases, QVAC output and VLM blocks to the new language."""
    if old_lang == new_lang:
        return

    case_id = st.session_state.get("case_id")
    base, vlm_suffix = split_vlm_suffix(st.session_state.case_text, old_lang)

    if case_id:
        new_base = case_text_for(case_id, new_lang)
    else:
        new_base, resolved = translate_case_text(base, old_lang, new_lang)
        if resolved:
            case_id = resolved
            st.session_state.case_id = case_id

    if vlm_suffix is not None:
        new_base = f"{new_base}\n\n{VLM_MARKERS[new_lang]}\n{placeholder_extraction(new_lang)}"

    st.session_state.case_text = new_base
    if case_id:
        st.session_state.case_id = case_id

    if st.session_state.vlm_extraction:
        st.session_state.vlm_extraction = placeholder_extraction(new_lang)

    had_qvac_output = bool(st.session_state.user_outputs.get("qvac", "").strip())
    _invalidate_qvac()

    cloud_has_content = any(
        st.session_state.user_outputs.get(k, "").strip()
        for k in ("chatgpt", "claude", "gemini")
    )
    notices = []
    if cloud_has_content:
        notices.append(t("lang.cloud_paste_notice", new_lang))
    if had_qvac_output:
        notices.append(t("lang.qvac_rerun_notice", new_lang))
    st.session_state.lang_switch_notice = " ".join(notices) if notices else None

    for key in ("case_editor",):
        if key in st.session_state:
            del st.session_state[key]
