from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import ImprovementSuggestion

logger = logging.getLogger(__name__)

class RecommendationsOutput(BaseModel):
    improvements: list[ImprovementSuggestion] = Field(
        description="A list of 3 to 6 actionable storytelling improvements.",
        min_length=2,
        max_length=6
    )

# 2. Enhanced Prompt: Added constraints to stop long dialogue generation
SYSTEM = """You are an elite Hollywood script doctor.

Guidelines for your analysis:
1. Be Extremely Concise: Keep every 'suggestion' short, direct, and impactful (MAXIMUM 15-20 words). 
2. No Scripting: Do NOT write long paragraphs or generate example dialogue lines. Tell the user what to fix, don't write it for them.
3. Be Specific: Point directly to the moment or action that needs adjustment.
4. Categorize Correctly: Strictly assign to 'pacing', 'conflict', 'dialogue', 'emotional_impact', or 'other'.
5. Short Rationale: Keep the 'rationale' to a single, brief sentence explaining the 'why'."""


async def analyze_recommendations(
    llm: LlmClient, *, script: str, model: str
) -> list[ImprovementSuggestion]:

    try:
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="recommendations",
            schema_model=RecommendationsOutput
        )

        output = RecommendationsOutput.model_validate(raw)

        unique_improvements: list[ImprovementSuggestion] = []
        seen_suggestions = set()

        for item in output.improvements:
            key = item.suggestion.strip().lower()
            if key not in seen_suggestions:
                seen_suggestions.add(key)
                unique_improvements.append(item)

        if len(unique_improvements) < 2:
            raise ValueError("Too few valid suggestions generated.")

        return unique_improvements

    except Exception as e:
        logger.exception(
            "[Recommendations Error] model=%s script_chars=%s err=%r",
            model,
            len(script),
            e,
        )
        
        # Fallback text ko bhi sort aur impactful banaya gaya hai
        return [
            ImprovementSuggestion(
                category="dialogue",
                suggestion="Replace direct questions with a physical action showing hesitation.",
                rationale="Specificity builds subtext and increases tension.",
            ),
            ImprovementSuggestion(
                category="pacing",
                suggestion="Insert a short beat right before the key truth is revealed.",
                rationale="Pauses increase suspense and emotional impact.",
            ),
            ImprovementSuggestion(
                category="emotional_impact",
                suggestion="End the scene on a character's physical reaction.",
                rationale="Forces the audience to feel the weight of the reveal.",
            ),
        ]