from __future__ import annotations

from analyzer.llm.client import LlmClient
import logging

logger = logging.getLogger(__name__)

SYSTEM = """You are a professional story summarizer.

Return ONLY valid JSON:
{
  "summary": string
}

Rules:
- Write the summary in exactly 3-4 short lines.
- Separate lines using newline characters (\\n).
- Base strictly on the provided script.
- Include:
  1. Main character
  2. Situation
  3. Conflict or tension
  4. Any reveal or turning point
- Do NOT invent details not present in the script.
- Keep it concise but specific (avoid generic phrases like "things change")."""


def validate_summary(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not (3 <= len(lines) <= 4):
        return False
    if len(text.split()) < 12:
        return False
    return True


def _normalize_summary_lines(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if 3 <= len(lines) <= 4:
        return "\n".join(lines)

    parts = []
    for p in t.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        s = p.strip()
        if s:
            parts.append(s)
    if len(parts) == 1:
        parts = [s.strip() for s in t.replace("!", ".").replace("?", ".").split(".") if s.strip()]

    parts = [p if p.endswith((".", "!", "?")) else p + "." for p in parts]
    parts = parts[:4]
    if len(parts) < 3:
        return t
    return "\n".join(parts)


async def summarize(llm: LlmClient, *, script: str, model: str) -> str:
    try:
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="summary"
        )

        summary = raw.get("summary", "")
        summary = _normalize_summary_lines(summary)

        if not validate_summary(summary):
            raise ValueError("Invalid summary format")

        return summary.strip()

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
