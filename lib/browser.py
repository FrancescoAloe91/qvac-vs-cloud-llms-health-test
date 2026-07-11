"""Apertura siti Cloud LLM nel browser (solo link, niente auto-incolla)."""

import subprocess
import webbrowser

from lib.i18n import t
from lib.tiers import CLOUD_KEYS, MODEL_CONFIG

_GEMINI_HL = {"en": "en", "it": "it"}


def cloud_url(model_key: str, lang: str = "en") -> str:
    """Return the cloud site URL, with locale hints where supported."""
    url = MODEL_CONFIG[model_key]["url"]
    if not url:
        return ""
    if model_key == "gemini":
        hl = _GEMINI_HL.get(lang, "en")
        return f"https://gemini.google.com/app?hl={hl}"
    return url


def copy_to_clipboard(text: str) -> bool:
    """Copia manuale su richiesta utente (pulsante Copia prompt)."""
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def open_single_tab(model_key: str, lang: str = "en") -> None:
    url = cloud_url(model_key, lang)
    if url:
        webbrowser.open_new_tab(url)


def open_all_cloud_tabs(lang: str = "en") -> dict:
    """Apre ChatGPT, Claude e Gemini in tab separate."""
    opened = []
    for key in CLOUD_KEYS:
        url = cloud_url(key, lang)
        if url:
            webbrowser.open_new_tab(url)
            opened.append(MODEL_CONFIG[key]["name"])
    return {
        "opened": opened,
        "note": t("browser.note", lang),
    }
