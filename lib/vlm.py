"""Vision module for report/MRI text extraction (simulated)."""

from lib.i18n import t

_PLACEHOLDER = {
    "en": """[SIMULATED VLM EXTRACTION]
Document type: medical imaging report
Main findings:
- Anatomical structure within normal dimensional limits
- Parenchymal signal/density to correlate with clinical picture
- No gross focal lesions in the explored field
Image quality: adequate for preliminary assessment.

NOTE: extraction performed entirely on-device. The file never left this device.""",
    "it": """[ESTRAZIONE VLM SIMULATA]
Tipologia documento: referto di imaging medico
Reperti principali rilevati:
- Struttura anatomica nei limiti dimensionali di norma
- Segnale/densita' del parenchima da correlare al quadro clinico
- Non evidenti lesioni focali grossolane nel campo esplorato
Qualita' immagine: adeguata per valutazione preliminare.

NOTA: estrazione eseguita interamente in locale. Il file non ha
lasciato questo dispositivo.""",
}


def placeholder_extraction(lang: str = "en") -> str:
    return _PLACEHOLDER.get(lang, _PLACEHOLDER["en"])


def extract_text(file_name: str, file_bytes: bytes, lang: str = "en") -> str:
    """Simulate text extraction from an uploaded report/MRI."""
    size_kb = len(file_bytes) / 1024
    header = t("vlm.file_header", lang, name=file_name, size=f"{size_kb:.0f}")
    return f"{header}\n\n{placeholder_extraction(lang)}"
