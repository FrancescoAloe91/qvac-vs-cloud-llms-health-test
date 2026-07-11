"""Clinical cases for the benchmark."""

from typing import Optional, Tuple

from lib.i18n import SUPPORTED_LANGS, t

CASE_IDS = ("case1", "case2", "case3", "case4", "case5")

_CASE_TEXT = {
    "en": {
        "case1": (
            "Male patient, 45 years old, presents to the ED with severe crushing chest "
            "pain for 40 minutes, radiating to the left arm and jaw, worsened by exertion "
            "and unrelieved by rest, with nausea, cold sweats and dyspnea. No change with "
            "respiration or position. History: smoker (20 cigarettes/day for 25 years), "
            "hypertension on ramipril, untreated dyslipidemia, family history of ischemic "
            "heart disease (father MI at 52). Took sildenafil (Viagra) 4 hours ago for "
            "erectile dysfunction. No known drug allergies. Exam: BP 160/95 mmHg (symmetric "
            "in both arms), HR 98 bpm regular, RR 22/min, SpO2 94% on room air, afebrile. "
            "ECG: ST-segment elevation >2 mm in leads II, III, aVF with reciprocal "
            "depression in I, aVL. Point-of-care troponin I: 0.8 ng/mL (elevated)."
        ),
        "case2": (
            "Female patient, 34 years old, reports recurrent episodes over 3 months of "
            "paresthesia in the right hemibody, transient monocular vision loss in the "
            "left eye with pain on eye movement (resolved in 2 weeks), and marked fatigue. "
            "One episode of diplopia 1 year ago attributed to stress. Exam: hyperreflexia "
            "and a positive Babinski sign on the right, positive Lhermitte's sign, "
            "red-green color desaturation in the left eye. Currently on combined oral "
            "contraceptives. Brain MRI with contrast: multiple T2/FLAIR hyperintense "
            "lesions in periventricular and juxtacortical white matter (>2 typical regions "
            "involved), one gadolinium-enhancing pontine lesion. Cervical spine MRI: no "
            "spinal cord lesions. Positive oligoclonal bands in CSF. Serum vitamin B12 and "
            "TSH within normal range."
        ),
        "case3": (
            "6-year-old child, fever 38.9°C for 24 hours (peak 39.4°C), abdominal pain "
            "initially periumbilical then migrating to the right iliac fossa, vomiting "
            "(2 episodes), food refusal. History: documented anaphylaxis to amoxicillin at "
            "age 3 (facial angioedema and respiratory distress). Exam: HR 118 bpm, RR "
            "24/min, positive Blumberg and Rovsing signs, tenderness at McBurney's point, "
            "guarding, no bowel movement for 12 hours. Labs: WBC 16,500/mm³ with 82% "
            "neutrophils, CRP 48 mg/L. Abdominal ultrasound: appendix not visualized due to "
            "bowel gas, minimal pericecal fluid."
        ),
        "case4": (
            "Male patient, 28 years old, brought to the ED by family for severe insomnia "
            "for 10 days, accelerated and disorganized speech, incongruent spending "
            "(€15,000 in 3 days), grandiose ideas and increasing irritability. Two major "
            "depressive episodes in history (at 22 and 25) treated with SSRIs, no prior "
            "manic episodes. History of stage 2 chronic kidney disease (eGFR 55 "
            "mL/min/1.73m², followed by nephrology). Denies substance use but family "
            "reports energy drink and OTC decongestant abuse. Vitals: HR 112 bpm, BP "
            "138/88 mmHg, mild tremor, afebrile. Urine toxicology pending. No structured "
            "self/other harm ideation at assessment."
        ),
        "case5": (
            "[ANONYMIZED TEMPLATE — fill without identifying data]\n"
            "Patient [sex], [age range, e.g. 40-50 years].\n"
            "Main symptoms: [describe symptoms and duration].\n"
            "Past medical history: [relevant conditions].\n"
            "Current medications: [drugs, doses optional].\n"
            "Tests already done: [relevant reports, no dates/facilities].\n"
            "Privacy note: do NOT include name, date of birth, ID, city, hospital "
            "or any data traceable to the person."
        ),
    },
    "it": {
        "case1": (
            "Paziente maschio, 45 anni, giunge in PS per forte dolore al petto "
            "oppressivo insorto da 40 minuti, irradiato al braccio sinistro e alla "
            "mandibola, peggiorato dallo sforzo e non alleviato dal riposo, "
            "accompagnato da nausea, sudorazione fredda e dispnea. Nessuna variazione "
            "con la respirazione o la postura. Anamnesi: fumatore (20 sigarette/die da "
            "25 anni), ipertensione arteriosa in terapia con ramipril, dislipidemia non "
            "trattata, familiarita' per cardiopatia ischemica (padre IMA a 52 anni). Ha "
            "assunto sildenafil (Viagra) 4 ore fa per disfunzione erettile. Nessuna "
            "allergia nota a farmaci. Esame obiettivo: PA 160/95 mmHg (simmetrica ai "
            "due arti), FC 98 bpm regolare, FR 22/min, SpO2 94% in aria ambiente, "
            "afebbrile. ECG: sopraslivellamento ST >2 mm in II, III, aVF con "
            "sottoslivellamento speculare in I, aVL. Troponina I point-of-care: "
            "0.8 ng/mL (elevata)."
        ),
        "case2": (
            "Paziente femmina, 34 anni, riferisce negli ultimi 3 mesi episodi "
            "ricorrenti di parestesie all'emisoma destro, calo del visus monoculare "
            "sinistro con dolore ai movimenti oculari (risoltosi in 2 settimane) e "
            "marcata astenia. Un episodio di diplopia 1 anno fa, attribuito a stress. "
            "Esame obiettivo: iperreflessia e segno di Babinski positivo a destra, "
            "segno di Lhermitte positivo, desaturazione cromatica rosso-verde "
            "nell'occhio sinistro. In terapia con contraccettivo orale combinato. "
            "RMN encefalo con mdc: multiple lesioni iperintense in T2/FLAIR nella "
            "sostanza bianca periventricolare e juxtacorticale (>2 sedi tipiche "
            "coinvolte), una lesione captante gadolinio in sede pontina. RMN midollo "
            "cervicale: nessuna lesione midollare. Bande oligoclonali positive nel "
            "liquor. Vitamina B12 sierica e TSH nella norma."
        ),
        "case3": (
            "Bambino di 6 anni, febbre 38.9 gradi C da 24 ore (picco massimo 39.4°C), "
            "dolore addominale inizialmente periombelicale poi migrato in fossa iliaca "
            "destra, vomito (2 episodi), rifiuto del cibo. Anamnesi: anafilassi ad "
            "amoxicillina a 3 anni (angioedema del volto e distress respiratorio, "
            "documentata). Esame obiettivo: FC 118 bpm, FR 24/min, segno di Blumberg e "
            "di Rovsing positivi, dolorabilita' alla palpazione nel punto di McBurney, "
            "difesa addominale, alvo chiuso alle feci da 12 ore. Esami: GB 16.500/mmc "
            "con neutrofilia 82%, PCR 48 mg/L. Ecografia addome: appendice non "
            "visualizzabile per meteorismo, minima falda liquida periappendicolare."
        ),
        "case4": (
            "Paziente maschio, 28 anni, condotto in PS dai familiari per grave "
            "insonnia da 10 giorni, eloquio accelerato e disorganizzato, spese "
            "incongrue (15.000 euro in 3 giorni), idee di grandezza e irritabilita' "
            "crescente. Due episodi depressivi maggiori in anamnesi (a 22 e 25 anni) "
            "trattati con SSRI, nessun episodio maniacale precedente. Anamnesi di "
            "insufficienza renale cronica stadio 2 (eGFR 55 mL/min/1.73m², in "
            "follow-up nefrologico). Nega uso di sostanze, ma i familiari riferiscono "
            "abuso di energy drink e decongestionanti da banco. Parametri vitali: FC "
            "112 bpm, PA 138/88 mmHg, lieve tremore, apiressia. Esame tossicologico "
            "urinario in corso. Non idee auto/eterolesive strutturate al momento "
            "della valutazione."
        ),
        "case5": (
            "[TEMPLATE ANONIMIZZATO - compilare senza dati identificativi]\n"
            "Paziente [sesso], [fascia d'eta', es. 40-50 anni].\n"
            "Sintomi principali: [descrivere sintomi e durata].\n"
            "Anamnesi patologica remota: [patologie pregresse rilevanti].\n"
            "Terapia in corso: [farmaci, senza dosaggi se non necessari].\n"
            "Esami gia' eseguiti: [referti rilevanti, senza date/strutture].\n"
            "Nota privacy: NON inserire nome, data di nascita, codice fiscale, "
            "citta', ospedale o qualsiasi dato riconducibile alla persona."
        ),
    },
}

VLM_MARKERS = {
    "en": "[VLM REPORT]",
    "it": "[REFERTO VLM]",
}

# Metadata used purely for presentation (icons/colors/teaching focus) — never
# touches the clinical prose itself, so keyword matching in lib/medpsy.py stays intact.
CASE_META = {
    "case1": {"icon": "🫀", "color": "#ef4444", "specialty_key": "case.specialty.cardio", "focus_key": "case.focus.case1"},
    "case2": {"icon": "🧠", "color": "#8b5cf6", "specialty_key": "case.specialty.neuro", "focus_key": "case.focus.case2"},
    "case3": {"icon": "🧒", "color": "#f59e0b", "specialty_key": "case.specialty.pediatric", "focus_key": "case.focus.case3"},
    "case4": {"icon": "🧩", "color": "#06b6d4", "specialty_key": "case.specialty.psych", "focus_key": "case.focus.case4"},
    "case5": {"icon": "✏️", "color": "#64748b", "specialty_key": "case.specialty.custom", "focus_key": "case.focus.case5"},
}


def case_meta(case_id: Optional[str]) -> dict:
    return CASE_META.get(case_id, CASE_META["case5"])


def case_options(lang: str) -> dict:
    """Label -> clinical text for selectbox."""
    return {t(f"cases.{cid}", lang): _CASE_TEXT[lang][cid] for cid in CASE_IDS}


def default_case_text(lang: str) -> str:
    return _CASE_TEXT[lang]["case1"]


def case_text_for(case_id: str, lang: str) -> str:
    return _CASE_TEXT[lang][case_id]


def resolve_case_id(text: str, lang: Optional[str] = None) -> Optional[str]:
    """Match clinical text to a preset case id, if possible."""
    normalized = text.strip()
    langs = (lang,) if lang else SUPPORTED_LANGS
    for lng in langs:
        for cid in CASE_IDS:
            if normalized == _CASE_TEXT[lng][cid].strip():
                return cid
    return None


def translate_case_text(text: str, from_lang: str, to_lang: str) -> Tuple[str, Optional[str]]:
    """Return equivalent case text in another language and case id if known."""
    if from_lang == to_lang:
        cid = resolve_case_id(text, from_lang)
        return text, cid

    cid = resolve_case_id(text, from_lang)
    if not cid:
        for lng in SUPPORTED_LANGS:
            cid = resolve_case_id(text, lng)
            if cid:
                break
    if cid:
        return _CASE_TEXT[to_lang][cid], cid
    return text, None


def split_vlm_suffix(case_text: str, lang: str) -> Tuple[str, Optional[str]]:
    """Split base case from an appended VLM block, if present."""
    for marker in VLM_MARKERS.values():
        if marker in case_text:
            base, _, suffix = case_text.partition(marker)
            return base.rstrip(), suffix.lstrip("\n")
    return case_text, None


def build_prompt(case_text: str, lang: str = "en") -> str:
    return t("prompt.template", lang, case=case_text)
