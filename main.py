from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from analyzer.api.routes import router as v1_router
from analyzer.config import get_settings
from analyzer.llm.client import build_llm_client, llm_client_kind
from analyzer.services.cache import CacheService

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    app.state.settings = settings
    app.state.http = httpx.AsyncClient(timeout=timeout)

    mode = settings.analysis_mode.lower().strip()
    if mode == "live" and not (settings.openai_api_key or settings.google_api_key):
        raise RuntimeError("ANALYSIS_MODE=live requires OPENAI_API_KEY and/or GOOGLE_API_KEY (or GEMINI_API_KEY)")
    prov = settings.llm_provider.lower().strip()
    if mode == "live":
        if prov == "openai" and not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY")
        if prov == "google" and not settings.google_api_key:
            raise RuntimeError("LLM_PROVIDER=google requires GOOGLE_API_KEY (or GEMINI_API_KEY)")

    app.state.llm = build_llm_client(app.state.http, settings)
    app.state.llm_kind = llm_client_kind(app.state.llm)
    app.state.cache = CacheService(settings)

    logger.info("startup complete environment=%s", settings.environment)
    yield
    await app.state.cache.close()
    await app.state.http.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/")
    async def index():
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            return {"detail": "UI not found. Build static/index.html."}
        return FileResponse(index_path)

    app.include_router(v1_router, prefix="/v1")
    if STATIC_DIR.is_dir():
        # html=True: /assets/ serves static/index.html (directory URL without html returns 404)
        app.mount("/assets", StaticFiles(directory=STATIC_DIR, html=True), name="assets")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
