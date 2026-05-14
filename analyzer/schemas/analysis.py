from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    scene: str = Field(..., min_length=1, max_length=8000)
    dialogue: str = Field(..., min_length=1, max_length=8000)


class EmotionalArcBeat(BaseModel):
    label: str = Field(..., description="Beat label, e.g. setup, confrontation, turn")
    summary: str
    dominant_emotions: list[str] = Field(default_factory=list)


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
    category: str = Field(..., description="pacing|conflict|dialogue|emotional_impact|other")
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
