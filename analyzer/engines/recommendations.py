from __future__ import annotations

import logging
from typing import Any

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import ImprovementSuggestion

logger = logging.getLogger(__name__)

SYSTEM = """You are a professional story editor.
Return ONLY valid JSON:
{
  "improvements": [
    {"category": "pacing|conflict|dialogue|emotional_impact|other", "suggestion": string, "rationale": string|null}
  ]
}
Rules:
- Provide 3-6 improvements.
- Each suggestion must be actionable and specific to the script.
- categories must be one of the allowed literals."""


async def analyze_recommendations(
    llm: LlmClient, *, script: str, model: str
) -> list[ImprovementSuggestion]:

    try:
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="recommendations"
        )

        items = _extract_improvements(raw)
        if items is None:
            raise ValueError("Invalid LLM response format")

        out: list[ImprovementSuggestion] = []

        seen = set()
        allowed_categories = {"pacing", "conflict", "dialogue", "emotional_impact", "other"}

        for it in items:
            if not isinstance(it, dict):
                continue

            try:
                cat = it.get("category")
                if isinstance(cat, str) and cat not in allowed_categories:
                    it["category"] = "other"
                validated = ImprovementSuggestion.model_validate(it)

                # filter duplicates
                key = validated.suggestion.strip().lower()
                if key in seen:
                    continue
                seen.add(key)

                out.append(validated)

            except Exception:
                continue

        # ensure minimum quality
        if len(out) < 2:
            raise ValueError("Too few valid suggestions")

        return out

    except Exception as e:
        logger.exception(
            "[Recommendations Error] model=%s script_chars=%s err=%r",
            model,
            len(script),
            e,
        )
        return [
            ImprovementSuggestion(
                category="dialogue",
                suggestion="Add one specific line that reveals subtext (fear, guilt, or defensiveness) instead of generic questions.",
                rationale="Specificity makes dialogue feel character-driven and increases tension.",
            ),
            ImprovementSuggestion(
                category="pacing",
                suggestion="Insert a short pause/beat right before the key reveal.",
                rationale="A beat increases suspense and gives the turning point more impact.",
            ),
            ImprovementSuggestion(
                category="emotional_impact",
                suggestion="Show a physical reaction immediately after the reveal (silence, breath, gesture).",
                rationale="Physical cues make emotions more believable and cinematic.",
            ),
        ]


def _extract_improvements(raw: object) -> list[dict[str, Any]] | None:
    if isinstance(raw, dict):
        direct = raw.get("improvements")
        if isinstance(direct, list):
            return [x for x in direct if isinstance(x, dict)]

        for key in ("suggestions", "recommendations", "items"):
            v = raw.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]

        nested = raw.get("analysis") or raw.get("result") or raw.get("data")
        if isinstance(nested, dict):
            direct2 = nested.get("improvements")
            if isinstance(direct2, list):
                return [x for x in direct2 if isinstance(x, dict)]

        return None

    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    return None
