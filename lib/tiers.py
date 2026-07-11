"""Tier Light / Medium / Premium — scelta utente, uguale per tutti i cloud."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TierProfile:
    key: str
    label: str
    description: str
    badge_color: str
    ttft_s: float
    tps: float
    latency_base_s: float
    detail_factor: float


TIERS: Dict[str, TierProfile] = {
    "light": TierProfile(
        key="light",
        label="Light",
        description="Risposta rapida e sintetica — 3 ipotesi principali, urgenza, 2 esami chiave.",
        badge_color="#6b7280",
        ttft_s=0.6,
        tps=90.0,
        latency_base_s=2.5,
        detail_factor=0.55,
    ),
    "medium": TierProfile(
        key="medium",
        label="Medium",
        description="Valutazione equilibrata — DDx completa, esami, red flags, piano iniziale.",
        badge_color="#3b82f6",
        ttft_s=1.1,
        tps=58.0,
        latency_base_s=4.0,
        detail_factor=0.82,
    ),
    "premium": TierProfile(
        key="premium",
        label="Premium",
        description="Valutazione specialistica esaustiva — scoring, stratificazione rischio, follow-up.",
        badge_color="#f5c518",
        ttft_s=2.0,
        tps=32.0,
        latency_base_s=6.5,
        detail_factor=1.0,
    ),
}

TIER_INSTRUCTIONS = {
    "light": (
        "Rispondi in modo conciso (max 200 parole). Elenca solo le 3 ipotesi "
        "diagnostiche principali, 2 esami chiave e il livello di urgenza."
    ),
    "medium": (
        "Fornisci una valutazione equilibrata: diagnosi differenziale ordinata, "
        "esami da richiedere, red flags e piano terapeutico iniziale."
    ),
    "premium": (
        "Fornisci una valutazione specialistica esaustiva: diagnosi differenziale "
        "completa con scoring di probabilita', esami prioritizzati, stratificazione "
        "del rischio, piano terapeutico dettagliato e follow-up."
    ),
}

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
        "name": "Gemini Pro",
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


def build_tier_prompt(base_prompt: str, tier_key: str, lang: str = "en") -> str:
    from lib.i18n import tier_instruction
    return f"{tier_instruction(tier_key, lang)}\n\n{base_prompt}"
