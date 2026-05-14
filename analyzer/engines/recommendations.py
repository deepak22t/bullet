from __future__ import annotations

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import ImprovementSuggestion


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


async def analyze_recommendations(llm: LlmClient, *, script: str, model: str) -> list[ImprovementSuggestion]:
    raw = await llm.complete_json(system=SYSTEM, user=script, model=model, task="recommendations")
    items = raw.get("improvements", raw) if isinstance(raw, dict) else []
    if isinstance(items, dict) and "improvements" in items:
        items = items["improvements"]
    if not isinstance(items, list):
        return []
    out: list[ImprovementSuggestion] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(ImprovementSuggestion.model_validate(it))
    return out
