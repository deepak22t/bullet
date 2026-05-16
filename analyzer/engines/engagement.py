from __future__ import annotations

import logging

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EngagementAnalysis, EngagementFactor

logger = logging.getLogger(__name__)

# 1. Dynamic System Prompt: AI decides the most relevant factors
SYSTEM = """You are an elite story engagement analyst.
Your objective is to quantify how captivating the script is for a reader or audience.

Rules for your analysis:
1. Overall Score: Provide a holistic engagement score from 0 (completely boring) to 100 (unputdownable).
2. Dynamic Factors: Identify the top 3 to 4 engagement factors that are MOST RELEVANT to this specific script. 
   - Choose names that fit the genre (e.g., 'comedic_timing', 'romantic_chemistry', 'mystery_hook', 'pacing', 'emotional_resonance', etc.).
   - Use simple snake_case format for the factor names.
3. Factor Scoring: Rate each identified factor from 0 to 100 and provide a precise rationale explaining why it earned that score.
4. Cliffhanger Analysis: If the scene ends on a suspenseful note, identify the specific moment and explain why it works. If no cliffhanger exists, leave it null."""


async def analyze_engagement(
    llm: LlmClient, *, script: str, model: str
) -> EngagementAnalysis:

    try:
        raw = await llm.complete_json(
            system=SYSTEM, 
            user=script, 
            model=model, 
            task="engagement",
            schema_model=EngagementAnalysis
        )
        
        result = EngagementAnalysis.model_validate(raw)
        
        # Fallback: Agar AI galti se ek bhi factor na de
        if not result.factors:
            raise ValueError("LLM generated no engagement factors.")
            
        return result

    except Exception as e:
        logger.exception(
            "[Engagement Error] model=%s script_chars=%s err=%r",
            model,
            len(script),
            e,
        )
        
        # Dynamic Fallback
        return EngagementAnalysis(
            engagement_score_0_100=0,
            factors=[
                EngagementFactor(
                    name="analysis_failed", 
                    score_0_100=0, 
                    rationale="Model could not analyze factors due to an error."
                )
            ],
            cliffhanger=None,
        )