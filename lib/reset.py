"""Funzioni di reset sessione Streamlit."""

import streamlit as st

from lib.cases import default_case_text
from lib.wallet import reset_wallet


def reset_session() -> None:
    """Azzera tutto incluso wallet a 0 USDT."""
    st.session_state.benchmark_results = {}
    st.session_state.user_outputs = {}
    st.session_state.browser_info = None
    st.session_state.case_text = default_case_text(st.session_state.get("lang", "en"))
    st.session_state.case_id = "case1"
    st.session_state.case_text_version = st.session_state.get("case_text_version", 0) + 1
    st.session_state.lang_switch_notice = None
    st.session_state.vlm_extraction = None
    st.session_state.selected_tier = "medium"
    st.session_state.use_gold_standard = False
    st.session_state.gold_standard_text = ""
    st.session_state.session_history = []
    st.session_state.sell_step = None
    st.session_state.qvac_thinking = ""
    st.session_state.wallet = reset_wallet()

    for key in list(st.session_state.keys()):
        if key.startswith(("out_", "case_editor_v", "case_seg_")) or key in (
            "tier_segmented", "gold_standard_input"
        ):
            del st.session_state[key]
