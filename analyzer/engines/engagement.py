from __future__ import annotations

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EngagementAnalysis


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
    raw = await llm.complete_json(system=SYSTEM, user=script, model=model, task="engagement")
    return EngagementAnalysis.model_validate(raw)
