from __future__ import annotations

import logging
import re

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EngagementAnalysis, EngagementFactor

logger = logging.getLogger(__name__)


SYSTEM = """You are a story engagement analyst.
Return ONLY valid JSON matching this shape:
{
  "engagement_score_0_100": integer 0-100,
  "factors": [
    {"name": string, "score_0_100": integer 0-100, "rationale": string}
  ],
  "cliffhanger": null | {"moment": string, "why_it_works": string}
}
Rules:
- Include factors for these exact name strings: opening_hook, character_conflict, tension, cliffhanger_potential
- Score holistically; factors may differ.
- cliffhanger should be null if none is present."""


async def analyze_engagement(llm: LlmClient, *, script: str, model: str) -> EngagementAnalysis:
    raw = None
    try:
        raw = await llm.complete_json(system=SYSTEM, user=script, model=model, task="engagement")
        raw2 = _sanitize_raw(raw)
        result = EngagementAnalysis.model_validate(raw2)
        result.factors = _ensure_required_factors(result.factors)
        return result
    except Exception as e:
        raw_keys = None
        try:
            if isinstance(raw, dict):
                raw_keys = sorted(raw.keys())
        except Exception:
            raw_keys = None
        logger.exception(
            "[Engagement Error] model=%s script_chars=%s raw_keys=%s err=%r",
            model,
            len(script),
            raw_keys,
            e,
        )
        return EngagementAnalysis(
            engagement_score_0_100=0,
            factors=_ensure_required_factors([]),
            cliffhanger=None,
        )


def _normalize_factor_name(name: object) -> str:
    if not isinstance(name, str):
        return ""
    n = name.strip().lower()
    n = re.sub(r"[^a-z0-9_]+", "", n)
    aliases = {
        "hook": "opening_hook",
        "opening": "opening_hook",
        "openinghook": "opening_hook",
        "opening_hook": "opening_hook",
        "conflict": "character_conflict",
        "characterconflict": "character_conflict",
        "character_conflict": "character_conflict",
        "tension": "tension",
        "cliffhanger": "cliffhanger_potential",
        "cliffhangerpotential": "cliffhanger_potential",
        "cliffhanger_potential": "cliffhanger_potential",
    }
    return aliases.get(n, n)


def _ensure_required_factors(factors: list[EngagementFactor]) -> list[EngagementFactor]:
    required = [
        "opening_hook",
        "character_conflict",
        "tension",
        "cliffhanger_potential",
    ]
    by_name = {f.name: f for f in factors if isinstance(f.name, str)}
    out: list[EngagementFactor] = []
    for name in required:
        f = by_name.get(name)
        if f is None:
            out.append(EngagementFactor(name=name, score_0_100=0, rationale="Unavailable."))
        else:
            out.append(f)
    return out


def _sanitize_raw(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}

    factors_in = raw.get("factors")
    if not isinstance(factors_in, list):
        return raw

    cleaned: list[dict] = []
    for it in factors_in:
        if not isinstance(it, dict):
            continue
        name = _normalize_factor_name(it.get("name"))
        score = it.get("score_0_100", 0)
        rationale = it.get("rationale", "")

        if not isinstance(rationale, str):
            rationale = str(rationale)

        if isinstance(score, bool):
            score = int(score)
        if isinstance(score, (int, float)):
            score = int(score)
        else:
            score = 0
        score = max(0, min(100, score))

        cleaned.append({"name": name, "score_0_100": score, "rationale": rationale})

    raw2 = dict(raw)
    raw2["factors"] = cleaned
    return raw2
