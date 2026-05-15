from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=20000)

    @field_validator("input_text")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v
        
class EmotionalArcBeat(BaseModel):
    label: str = Field(..., description="Beat label, e.g. setup, confrontation, turn")
    summary: str
    dominant_emotions: list[str] = Field(default_factory=list)
    transition: str | None = None
    intensity_0_100: int | None = Field(default=None, ge=0, le=100)


class EmotionAnalysis(BaseModel):
    overall_tone: str
    dominant_emotions: list[str]
    arc_beats: list[EmotionalArcBeat] = Field(default_factory=list)
    notes: str | None = None


class EngagementFactor(BaseModel):
    name: str
    score_0_100: int = Field(..., ge=0, le=100)
    rationale: str


class CliffhangerInsight(BaseModel):
    moment: str
    why_it_works: str


class EngagementAnalysis(BaseModel):
    engagement_score_0_100: int = Field(..., ge=0, le=100)
    factors: list[EngagementFactor]
    cliffhanger: CliffhangerInsight | None = None


class ImprovementSuggestion(BaseModel):
    category: Literal["pacing", "conflict", "dialogue", "emotional_impact", "other"]
    suggestion: str
    rationale: str | None = None


class AnalysisMeta(BaseModel):
    request_id: str
    latency_ms: int
    mode: str
    provider: str | None = Field(default=None, description="openai|google|mock")
    model: str | None = None
    partial: bool = False
    errors: dict[str, str] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    summary: str
    emotion: EmotionAnalysis
    engagement: EngagementAnalysis
    improvements: list[ImprovementSuggestion]
    meta: AnalysisMeta
