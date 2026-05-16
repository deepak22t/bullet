from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from analyzer.config import Settings
from analyzer.engines.emotion import analyze_emotion
from analyzer.engines.engagement import analyze_engagement
from analyzer.engines.recommendations import analyze_recommendations
from analyzer.engines.summary import summarize
from analyzer.llm.client import LlmClient
from analyzer.schemas.analysis import (
    AnalysisMeta,
    AnalysisResponse,
    AnalyzeRequest,
    EmotionAnalysis,
    EngagementAnalysis,
    EngagementFactor,
    ImprovementSuggestion,
)
from analyzer.services.normalize import format_script

logger = logging.getLogger(__name__)


def resolve_text_model(settings: Settings, llm_kind: str) -> str:
    if llm_kind == "google":
        if settings.llm_model.lower().startswith("gemini"):
            return settings.llm_model
        return settings.gemini_model
    return settings.llm_model

def _fallback_emotion(message: str) -> EmotionAnalysis:
    return EmotionAnalysis(
        overall_tone="unavailable",
        dominant_emotions=[],
        arc_beats=[],
        notes=message,
    )


def _fallback_engagement(message: str) -> EngagementAnalysis:
    return EngagementAnalysis(
        engagement_score_0_100=0,
        factors=[
            EngagementFactor(name="opening_hook", score_0_100=0, rationale=message),
            EngagementFactor(name="character_conflict", score_0_100=0, rationale=message),
            EngagementFactor(name="tension", score_0_100=0, rationale=message),
            EngagementFactor(name="cliffhanger_potential", score_0_100=0, rationale=message),
        ],
        cliffhanger=None,
    )


async def run_analysis(
    *,
    llm: LlmClient,
    req: AnalyzeRequest,
    settings: Settings,
    request_id: str,
    llm_kind: str,
) -> AnalysisResponse:
    script = format_script(req)
    model = resolve_text_model(settings, llm_kind)
    sem = asyncio.Semaphore(max(1, settings.max_concurrent_llm_calls))
    errors: dict[str, str] = {}

    async def gated(coro: Any) -> Any:
        async with sem:
            return await coro

    t0 = time.perf_counter()

    emotion_task = gated(analyze_emotion(llm, script=script, model=model))
    engagement_task = gated(analyze_engagement(llm, script=script, model=model))
    recommendations_task = gated(analyze_recommendations(llm, script=script, model=model))
    summary_task = gated(summarize(llm, script=script, model=model))

    emotion_r, engagement_r, rec_r, sum_r = await asyncio.gather(
        emotion_task,
        engagement_task,
        recommendations_task,
        summary_task,
        return_exceptions=True,
    )

    emotion: EmotionAnalysis
    if isinstance(emotion_r, Exception):
        errors["emotion"] = repr(emotion_r)
        emotion = _fallback_emotion("Emotion engine failed; see meta.errors.")
    else:
        emotion = emotion_r

    engagement: EngagementAnalysis
    if isinstance(engagement_r, Exception):
        errors["engagement"] = repr(engagement_r)
        engagement = _fallback_engagement("Engagement engine failed; see meta.errors.")
    else:
        engagement = engagement_r

    improvements: list[ImprovementSuggestion]
    if isinstance(rec_r, Exception):
        errors["recommendations"] = repr(rec_r)
        improvements = [
            ImprovementSuggestion(
                category="other",
                suggestion="Recommendations engine failed. Retry the request.",
                rationale=errors["recommendations"],
            )
        ]
    else:
        improvements = rec_r

    summary: str
    if isinstance(sum_r, Exception):
        errors["summary"] = repr(sum_r)
        logger.exception(
            "summary engine failed request_id=%s llm_kind=%s model=%s",
            request_id,
            llm_kind,
            model,
            exc_info=sum_r,
        )
        summary = "Summary unavailable."
    else:
        summary = sum_r

    latency_ms = int((time.perf_counter() - t0) * 1000)
    mode = settings.analysis_mode
    if settings.analysis_mode == "auto":
        mode = "live" if (settings.openai_api_key or settings.google_api_key) else "mock"

    meta = AnalysisMeta(
        request_id=request_id,
        latency_ms=latency_ms,
        mode=mode,
        provider=llm_kind,
        model=model if mode == "live" else None,
        partial=bool(errors),
        errors=errors,
    )

    response = AnalysisResponse(
        summary=summary,
        emotion=emotion,
        engagement=engagement,
        improvements=improvements,
        meta=meta,
    )
    return response

def new_request_id() -> str:
    return str(uuid.uuid4())
