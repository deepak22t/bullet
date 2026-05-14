from __future__ import annotations

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EmotionAnalysis


SYSTEM = """You are a screenplay/story emotion analyst.
Return ONLY valid JSON matching this shape:
{
  "overall_tone": string,
  "dominant_emotions": string[],
  "arc_beats": [{"label": string, "summary": string, "dominant_emotions": string[]}],
  "notes": string | null
}
Rules:
- Base claims strictly on the provided script.
- arc_beats should follow chronological order through the scene.
- Keep emotions concrete (e.g., shame, relief), not vague filler."""


async def analyze_emotion(llm: LlmClient, *, script: str, model: str) -> EmotionAnalysis:
    raw = await llm.complete_json(system=SYSTEM, user=script, model=model, task="emotion")
    return EmotionAnalysis.model_validate(raw)
