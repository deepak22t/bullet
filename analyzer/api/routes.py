from fastapi import APIRouter, Request
from analyzer.schemas.analysis import AnalysisResponse, AnalyzeRequest
from analyzer.services.orchestrator import new_request_id, resolve_text_model, run_analysis

router = APIRouter(tags=["analysis"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_script(request: Request, body: AnalyzeRequest) -> AnalysisResponse:

    settings = request.app.state.settings
    llm = request.app.state.llm
    llm_kind = getattr(request.app.state, "llm_kind", "mock")
    rid = getattr(request.state, "request_id", None) or new_request_id()

    cache = getattr(request.app.state, "cache", None)
    model = resolve_text_model(settings, llm_kind)
    payload = {
        "req": body.model_dump(),
        "llm_kind": llm_kind,
        "analysis_mode": settings.analysis_mode,
        "llm_provider": settings.llm_provider,
        "model": model,
    }

    if cache:
        cached_data = await cache.get_analysis(payload)
        if cached_data is not None:
            cached_data.meta.request_id = rid
            return cached_data

    res = await run_analysis(
        llm=llm,
        req=body,
        settings=settings,
        request_id=rid,
        llm_kind=llm_kind,
    )

    if res is None:
        raise ValueError("run_analysis returned None")

    if cache:
        await cache.set_analysis(payload, res)

    return res
