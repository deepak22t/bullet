from fastapi import APIRouter, Request

from analyzer.schemas.analysis import AnalysisResponse, AnalyzeRequest
from analyzer.services.orchestrator import new_request_id, run_analysis

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_script(request: Request, body: AnalyzeRequest) -> AnalysisResponse:

    settings = request.app.state.settings
    llm = request.app.state.llm
    llm_kind = getattr(request.app.state, "llm_kind", "mock")
    rid = getattr(request.state, "request_id", None) or new_request_id()
    return await run_analysis(
        llm=llm,
        req=body,
        settings=settings,
        request_id=rid,
        llm_kind=llm_kind,
    )
