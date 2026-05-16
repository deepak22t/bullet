from __future__ import annotations

import logging
from pydantic import BaseModel, Field
from analyzer.llm.client import LlmClient

logger = logging.getLogger(__name__)

# 1. Define the strict Pydantic structure
class StorySummary(BaseModel):
    summary: str = Field(
        description="A 3 to 4 line summary of the script. Separate lines using newline characters."
    )

# 2. Clean Prompt: Focus only on story rules, no JSON formatting instructions!
SYSTEM = """You are a professional story summarizer.

Rules:
- Write the summary in exactly 3-4 short lines.
- Separate lines using newline characters (\n).
- Base strictly on the provided script.
- Include:
  1. Main character
  2. Situation
  3. Conflict or tension
  4. Any reveal or turning point
- Do NOT invent details not present in the script.
- Keep it concise but specific (avoid generic phrases like "things change")."""

async def summarize(llm: LlmClient, *, script: str, model: str) -> str:
    try:
        # Pass the Pydantic class to the LLM client as a Schema Blueprint
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="summary",
            schema_model=StorySummary 
        )

        summary_text = raw.get("summary", "")
        if not summary_text:
            raise ValueError("LLM returned an empty summary.")
        return summary_text

    except Exception as e:
        logger.exception(
            "[Summary Error] model=%s script_chars=%s err=%r",
            model,
            len(script),
            e,
        )
        return (
            "A character receives an unexpected message after a long silence.\n"
            "A tense exchange brings unresolved conflict back to the surface.\n"
            "A truth is revealed that reframes what happened in the past.\n"
            "The moment leaves the characters facing new emotional stakes."
        )