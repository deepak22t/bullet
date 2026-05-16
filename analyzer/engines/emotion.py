from __future__ import annotations

import logging

from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import EmotionAnalysis,EmotionalArcBeat
logger = logging.getLogger(__name__)

# 1. Enhanced Prompt: Added strict limits for brevity and impact
SYSTEM = """You are an elite Hollywood script analyst specializing in character psychology.

Guidelines for your analysis:
1. Chronological Tracking: Map emotional shifts exactly as they occur.
2. Extreme Brevity: Keep the 'summary' and 'transition' extremely short and punchy (MAXIMUM 10 to 15 words each). Use a single sentence.
3. Specificity: Tie the beat to a specific line or action, but do not overwrite.
4. Deep Emotions: Identify subtext and complex feelings (e.g., masking fear with anger).
5. Intensity Rating: Rate emotional intensity from 0 to 100.
6. Grounded Reality: Base analysis purely on the text. No invented events."""


async def analyze_emotion(
    llm: LlmClient, *, script: str, model: str
) -> EmotionAnalysis:

    try:
        raw = await llm.complete_json(
            system=SYSTEM,
            user=script,
            model=model,
            task="emotion",
            schema_model=EmotionAnalysis
        )

        result = EmotionAnalysis.model_validate(raw)
        # Safely handle models that generate incomplete arrays
        if len(result.arc_beats) == 0:
            result.arc_beats = [
                EmotionalArcBeat(
                    label="Baseline", 
                    summary="Scene establishes an initial state.", 
                    dominant_emotions=["neutral"], 
                    transition="No prior context.", 
                    intensity_0_100=40
                ),
                EmotionalArcBeat(
                    label="Progression", 
                    summary="The emotional stakes shift as the scene evolves.", 
                    dominant_emotions=["tension"], 
                    transition="Tension naturally escalates.", 
                    intensity_0_100=60
                )
            ]
        elif len(result.arc_beats) == 1:
            b0 = result.arc_beats[0]
            current_intensity = b0.intensity_0_100 if b0.intensity_0_100 is not None else 50
            result.arc_beats.append(
                EmotionalArcBeat(
                    label="Resolution",
                    summary="The scene reaches its concluding emotional state.",
                    dominant_emotions=b0.dominant_emotions,
                    transition="The initial emotion settles into a new baseline.",
                    intensity_0_100=min(100, current_intensity + 15)
                )
            )

        return result
    

    except Exception as e:
        logger.exception(
            "[Emotion Error] model=%s script_chars=%s err=%r",
            model,
            len(script),
            e,
        )
        
        # Fallback bhi chota aur crisp kar diya gaya hai
        return EmotionAnalysis.model_validate({
            "overall_tone": "unavailable",
            "dominant_emotions": [],
            "arc_beats": [
                {
                    "label": "setup",
                    "summary": "Initial emotional context could not be extracted.",
                    "dominant_emotions": [],
                    "transition": "Unavailable.",
                    "intensity_0_100": 40,
                },
                {
                    "label": "turn",
                    "summary": "Shift in emotional state details unavailable.",
                    "dominant_emotions": [],
                    "transition": "Unavailable.",
                    "intensity_0_100": 60,
                },
            ],
            "notes": "Fallback emotion arc applied.",
        })