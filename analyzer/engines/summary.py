from __future__ import annotations

from analyzer.llm.client import LlmClient


SYSTEM = """You write tight story summaries for creators.
Return ONLY valid JSON: {"summary": string}
Rules:
- 2-4 sentences max.
- No spoilers beyond what is explicitly in the script.
- Focus on premise + conflict + turn."""


async def summarize(llm: LlmClient, *, script: str, model: str) -> str:
    raw = await llm.complete_json(system=SYSTEM, user=script, model=model, task="summary")
    summary = raw.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        return "Summary unavailable."
    return summary.strip()
