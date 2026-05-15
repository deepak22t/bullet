from __future__ import annotations

import logging
import re
from typing import Any

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EmotionAnalysis

logger = logging.getLogger(__name__)


SYSTEM = """You are an expert story emotion analyst.

Return ONLY valid JSON:
{
  "overall_tone": string,
  "dominant_emotions": string[],
  "arc_beats": [
    {
      "label": string,
      "summary": string,
      "dominant_emotions": string[],
      "transition": string,
      "intensity_0_100": integer 0-100
    }
  ],
  "notes": string | null
}

Rules:
- Analyze how emotions evolve across the scene.
- arc_beats must follow chronological order.
- Each arc beat must:
  1. Refer to a specific moment or line in the script
  2. Describe the emotional state (not just events)
  3. Include dominant emotions (concrete words like fear, relief, guilt)
  4. Include a "transition" explaining how emotion shifts from previous beat
- Avoid generic labels like "start/middle/end" — use meaningful labels.
- Do NOT invent events not present in the script.
- Keep insights specific and grounded in the script.
"""


async def analyze_emotion(
    llm: LlmClient, *, script: str, model: str
) -> EmotionAnalysis:

    raw = None
    try:
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="emotion"
        )

        raw2 = _sanitize_raw(raw)
        result = EmotionAnalysis.model_validate(raw2)
        if len(result.arc_beats) < 2:
            result.arc_beats = _pad_beats(result.arc_beats)
        return result

    except Exception as e:
        raw_keys = None
        try:
            if isinstance(raw, dict):
                raw_keys = sorted(raw.keys())
        except Exception:
            raw_keys = None

        logger.exception(
            "[Emotion Error] model=%s script_chars=%s raw_keys=%s err=%r",
            model,
            len(script),
            raw_keys,
            e,
        )
        return EmotionAnalysis(
            overall_tone="unavailable",
            dominant_emotions=[],
            arc_beats=[
                {
                    "label": "setup",
                    "summary": "Emotional context is introduced but could not be reliably extracted.",
                    "dominant_emotions": [],
                    "transition": "Unavailable.",
                    "intensity_0_100": 40,
                },
                {
                    "label": "turn",
                    "summary": "A shift in emotional state occurs but details were unavailable.",
                    "dominant_emotions": [],
                    "transition": "Unavailable.",
                    "intensity_0_100": 60,
                },
            ],
            notes="Fallback emotion arc due to processing issue.",
        )


def _normalize_key(k: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", k.strip().lower())


def _coerce_str_list(v: object) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        parts = [p.strip() for p in re.split(r"[,;/\n]+", s) if p.strip()]
        return parts[:12]
    return []


def _sanitize_beat(b: object) -> dict[str, Any]:
    if not isinstance(b, dict):
        return {}
    label = b.get("label") if isinstance(b.get("label"), str) else ""
    summary = b.get("summary") if isinstance(b.get("summary"), str) else ""
    dom = _coerce_str_list(b.get("dominant_emotions"))
    transition = b.get("transition") if isinstance(b.get("transition"), str) else None
    intensity = b.get("intensity_0_100")
    if isinstance(intensity, bool):
        intensity = int(intensity)
    if isinstance(intensity, (int, float)):
        intensity = int(intensity)
        intensity = max(0, min(100, intensity))
    else:
        intensity = None
    out: dict[str, Any] = {
        "label": label.strip() or "beat",
        "summary": summary.strip() or "—",
        "dominant_emotions": dom,
        "transition": transition.strip() if isinstance(transition, str) and transition.strip() else None,
        "intensity_0_100": intensity,
    }
    return out


def _pad_beats(beats: list[Any]) -> list[Any]:
    if len(beats) >= 2:
        return beats
    if len(beats) == 1:
        b0 = beats[0]
        intensity0 = getattr(b0, "intensity_0_100", None)
        if not isinstance(intensity0, int):
            intensity0 = 45
        return [
            b0,
            {
                "label": "turn",
                "summary": "An emotional shift occurs as new information lands.",
                "dominant_emotions": getattr(b0, "dominant_emotions", []) or [],
                "transition": "Intensity rises from the initial state as stakes clarify.",
                "intensity_0_100": min(100, intensity0 + 20),
            },
        ]
    return [
        {
            "label": "setup",
            "summary": "The scene establishes an emotional baseline.",
            "dominant_emotions": [],
            "transition": "No prior context.",
            "intensity_0_100": 40,
        },
        {
            "label": "turn",
            "summary": "A turning point shifts the emotional direction.",
            "dominant_emotions": [],
            "transition": "Tension increases as the reveal approaches.",
            "intensity_0_100": 65,
        },
    ]


def _sanitize_raw(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    norm_map = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        nk = _normalize_key(k)
        norm_map[nk] = v

    overall_tone = norm_map.get("overalltone")
    if overall_tone is None:
        overall_tone = norm_map.get("overalltole")
    if not isinstance(overall_tone, str):
        overall_tone = "unavailable"

    dom = norm_map.get("dominantemotions")
    if dom is None:
        dom = norm_map.get("dominantemotion")
    dominant_emotions = _coerce_str_list(dom)

    beats_raw = norm_map.get("arcbeats")
    if not isinstance(beats_raw, list):
        beats_raw = raw.get("arc_beats") if isinstance(raw.get("arc_beats"), list) else []
    beats_clean = [_sanitize_beat(b) for b in beats_raw]
    beats_clean = [b for b in beats_clean if b]

    notes = raw.get("notes")
    if not isinstance(notes, str):
        notes = None

    return {
        "overall_tone": overall_tone.strip() or "unavailable",
        "dominant_emotions": dominant_emotions,
        "arc_beats": beats_clean,
        "notes": notes,
    }
