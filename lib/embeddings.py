"""Local semantic-similarity engine — real embeddings, no API calls, no cheating.

Runs a tiny embedding model (all-minilm, CPU-only) on the same local Ollama
server used for MedPsy, so the diagnostic KPIs can compare what models
*mean*, not only which exact words they used. This keeps the "same weapons
for everyone" principle intact: it is a small, real, on-device model that
scores every model's text identically — QVAC included — not a shortcut or
a canned number.
"""

import json
import math
import os
import urllib.error
import urllib.request

OLLAMA_HOST = os.environ.get("QVAC_OLLAMA_HOST", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("QVAC_EMBED_MODEL", "all-minilm-cpu")

# Cosine similarity between two *unrelated* short clinical sentences rarely
# drops below ~0.20 with this model (shared domain vocabulary alone gives a
# baseline), so that floor is used when rescaling to an intuitive 0-100%
# range: 100% still means "same meaning", but 0% now means "unrelated"
# instead of a raw ~20-30% floor that would read as false partial agreement.
_FLOOR = 0.20
_MAX_CACHE = 500

_cache: dict = {}


def embed(text: str, timeout: float = 8.0):
    """Embed a short text with the local model. Returns None on any failure
    (server unreachable, model missing, timeout) so callers can degrade
    gracefully instead of crashing or faking a score."""
    text = (text or "").strip()
    if not text:
        return None
    if text in _cache:
        return _cache[text]
    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/embed",
            data=json.dumps({"model": EMBED_MODEL, "input": text[:2000]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        vec = (data.get("embeddings") or [None])[0]
    except Exception:
        return None
    if vec:
        if len(_cache) >= _MAX_CACHE:
            _cache.clear()
        _cache[text] = vec
    return vec


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_similarity_pct(text_a: str, text_b: str):
    """Meaning-level similarity between two texts, 0-100%, or ``None`` if the
    local embedding model is unreachable. Rescaled with a floor so unrelated
    clinical content reads near 0% instead of this model's raw ~20-30%
    baseline for any two clinical sentences."""
    va, vb = embed(text_a), embed(text_b)
    if va is None or vb is None:
        return None
    raw = max(0.0, min(1.0, _cosine(va, vb)))
    rescaled = max(0.0, (raw - _FLOOR) / (1 - _FLOOR)) * 100
    return round(min(rescaled, 100.0), 1)


def embeddings_available() -> bool:
    """Cheap reachability probe used by the UI to explain a missing KPI."""
    return embed("clinical diagnosis") is not None
