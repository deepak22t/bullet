from fastapi import APIRouter, Request
import json
from analyzer.schemas.analysis import AnalysisResponse, AnalyzeRequest
from analyzer.services.orchestrator import new_request_id, run_analysis

router = APIRouter(tags=["analysis"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_script(request: Request, body: AnalyzeRequest) -> AnalysisResponse:

    settings = request.app.state.settings
    llm = request.app.state.llm
    llm_kind = getattr(request.app.state, "llm_kind", "mock")
    rid = getattr(request.state, "request_id", None) or new_request_id()

    cache = getattr(request.app.state, "cache", None)

    # ✅ Use payload (NOT string key)
    payload = body.model_dump()
    print("cache payload:", payload)

    # ✅ Step 1: Try cache
    if cache:
        cached_data = await cache.get_analysis(payload)
        print("cached_data:", cached_data)

        if cached_data is not None:
            print("returning cached response")
            cached_data.meta.request_id = rid
            return cached_data

    # ✅ Step 2: Run fresh analysis
    print("running fresh analysis")

    res = await run_analysis(
        llm=llm,
        req=body,
        settings=settings,
        request_id=rid,
        llm_kind=llm_kind,
    )

    if res is None:
        raise ValueError("run_analysis returned None")

    # ✅ Step 3: Store in cache (PASS OBJECT, NOT DICT)
    if cache:
        await cache.set_analysis(payload, res)
        print("cache set")

    return res