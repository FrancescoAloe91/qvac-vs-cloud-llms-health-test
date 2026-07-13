"""Model registry and QVAC prompt helper.

QVAC MedPsy 4B is a single on-device model — there is no Lite/Pro split like
cloud vendors. One balanced clinical instruction is prepended for local inference;
the same base prompt is copied for the cloud sites.
"""

from typing import Dict


MODEL_CONFIG = {
    "chatgpt": {
        "name": "ChatGPT",
        "vendor": "OpenAI",
        "cloud": True,
        "url": "https://chatgpt.com",
        "icon": "🟢",
        "color": "#10a37f",
    },
    "claude": {
        "name": "Claude",
        "vendor": "Anthropic",
        "cloud": True,
        "url": "https://claude.ai",
        "icon": "🟠",
        "color": "#d97706",
    },
    "gemini": {
        "name": "Gemini",
        "vendor": "Google",
        "cloud": True,
        "url": "https://gemini.google.com/app",
        "icon": "🔵",
        "color": "#8ab4f8",
    },
    "qvac": {
        "name": "Tether QVAC MedPsy 4B",
        "vendor": "Tether · on-device",
        "cloud": False,
        "url": None,
        "icon": "🟩",
        "color": "#00d09c",
    },
}

CLOUD_KEYS = ("chatgpt", "claude", "gemini")


def build_qvac_prompt(base_prompt: str, lang: str = "en") -> str:
    """Prepend MedPsy's standard balanced clinical instruction for local inference."""
    from lib.i18n import qvac_instruction

    return f"{qvac_instruction(lang)}\n\n{base_prompt}"
