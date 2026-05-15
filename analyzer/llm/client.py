from __future__ import annotations

import json
import logging
from typing import Any, Literal, Protocol, runtime_checkable
import asyncio
import httpx

from analyzer.config import Settings

logger = logging.getLogger(__name__)


MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


LlmTask = Literal["emotion", "engagement", "recommendations", "summary"]



@runtime_checkable
class LlmClient(Protocol):
    async def complete_json(
        self, *, system: str, user: str, model: str, task: LlmTask = "summary"
    ) -> dict[str, Any]: ...


class OpenAiJsonClient:
    """Isolated provider adapter: chat completions with JSON object output."""

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings

    async def complete_json(
        self, *, system: str, user: str, model: str, task: LlmTask = "summary"
    ) -> dict[str, Any]:
        _ = task
        key = self._settings.openai_api_key
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        url = f"{self._settings.openai_base_url}"
        payload = {
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._http.post(url, headers=headers, json=payload)
                resp.raise_for_status()

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                if not isinstance(content, str):
                    raise ValueError("Invalid response format from LLM")

                # ✅ Safe JSON parsing
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON returned by LLM: {content}")

            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"LLM request failed after retries: {e}")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

class GoogleGeminiJsonClient:
    """Google AI Studio / Gemini generateContent with JSON response MIME type."""

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings

    def _gemini_model_id(self, model: str) -> str:
        m = model.strip()
        if m.lower().startswith("gemini"):
            return m
        return self._settings.gemini_model

    async def complete_json(
        self, *, system: str, user: str, model: str, task: LlmTask = "summary"
    ) -> dict[str, Any]:
        _ = task
        key = self._settings.google_api_key
        if not key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is not set")

        mid = self._gemini_model_id(model)
        base = self._settings.google_genai_base_url.rstrip("/")
        url = f"{base}/models/{mid}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        resp = await self._http.post(url, params={"key": key}, json=payload)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Gemini HTTP {resp.status_code}: {detail}")

        data = resp.json()
        candidates = data.get("candidates")
        if not candidates:
            raise ValueError(f"Gemini returned no candidates: {data!r}")

        parts = candidates[0].get("content", {}).get("parts") or []
        if not parts or not isinstance(parts[0].get("text"), str):
            raise ValueError(f"Unexpected Gemini response shape: {data!r}")

        return json.loads(parts[0]["text"])


class MockLlmClient:
    """Fast, deterministic path for demos, load tests, and CI without external calls."""

    async def complete_json(
        self, *, system: str, user: str, model: str, task: LlmTask = "summary"
    ) -> dict[str, Any]:
        _ = (system, user, model)
        if task == "emotion":
            return {
                "overall_tone": "tense, unresolved",
                "dominant_emotions": ["curiosity", "relief", "defensiveness"],
                "arc_beats": [
                    {
                        "label": "setup",
                        "summary": "A long-delayed message reopens a wound.",
                        "dominant_emotions": ["unease"],
                        "transition": "No prior context; unease builds from silence breaking.",
                        "intensity_0_100": 48,
                    },
                    {
                        "label": "revelation",
                        "summary": "New information reframes blame for a past accident.",
                        "dominant_emotions": ["shock", "catharsis"],
                        "transition": "Unease spikes into shock as truth is revealed, then eases into catharsis.",
                        "intensity_0_100": 82,
                    },
                ],
                "notes": (
                    "Mock response: set OPENAI_API_KEY or GOOGLE_API_KEY (and ANALYSIS_MODE=live) "
                    "for real analysis."
                ),
            }
        if task == "engagement":
            return {
                "engagement_score_0_100": 74,
                "factors": [
                    {
                        "name": "opening_hook",
                        "score_0_100": 70,
                        "rationale": "Immediate question signals stakes and history.",
                    },
                    {
                        "name": "character_conflict",
                        "score_0_100": 78,
                        "rationale": "Interpersonal tension implied by the ex and the unanswered past.",
                    },
                    {
                        "name": "tension",
                        "score_0_100": 72,
                        "rationale": "Short lines increase pressure and pacing.",
                    },
                    {
                        "name": "cliffhanger_potential",
                        "score_0_100": 76,
                        "rationale": "Final line reframes guilt and invites continuation.",
                    },
                ],
                "cliffhanger": {
                    "moment": "Arjun reveals the accident was not Riya's fault.",
                    "why_it_works": "It reverses an assumed moral burden and creates a new emotional problem: what now?",
                },
            }
        if task == "recommendations":
            return {
                "improvements": [
                    {
                        "category": "dialogue",
                        "suggestion": "Add one line of physical behavior to anchor emotion (hands, breath, silence).",
                        "rationale": "Increases subtext without exposition.",
                    },
                    {
                        "category": "emotional_impact",
                        "suggestion": "Let Riya resist believing the truth for one beat before the scene turns.",
                        "rationale": "Creates a clearer emotional arc beat between shock and acceptance.",
                    },
                    {
                        "category": "pacing",
                        "suggestion": "Insert a pause/stage direction between question and revelation.",
                        "rationale": "Lets tension land before the twist.",
                    },
                ]
            }
        return {
            "summary": (
                "Mock summary: two characters confront a delayed truth about an accident, "
                "shifting blame and reopening unresolved feelings."
            )
        }


def llm_client_kind(client: LlmClient) -> str:
    if isinstance(client, OpenAiJsonClient):
        return "openai"
    if isinstance(client, GoogleGeminiJsonClient):
        return "google"
    return "mock"


def _pick_remote_client(http: httpx.AsyncClient, settings: Settings) -> LlmClient:
    prov = settings.llm_provider.lower().strip()
    has_oai = bool(settings.openai_api_key)
    has_g = bool(settings.google_api_key)

    if prov == "openai":
        if not has_oai:
            raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY")
        return OpenAiJsonClient(http, settings)
    if prov == "google":
        if not has_g:
            raise RuntimeError("LLM_PROVIDER=google requires GOOGLE_API_KEY (or GEMINI_API_KEY)")
        return GoogleGeminiJsonClient(http, settings)

    # auto
    if has_oai:
        return OpenAiJsonClient(http, settings)
    if has_g:
        return GoogleGeminiJsonClient(http, settings)
    raise RuntimeError("ANALYSIS_MODE=live requires OPENAI_API_KEY and/or GOOGLE_API_KEY")


def build_llm_client(http: httpx.AsyncClient, settings: Settings) -> LlmClient:
    mode = settings.analysis_mode.lower().strip()
    if mode == "mock":
        return MockLlmClient()
    if mode == "live":
        return _pick_remote_client(http, settings)

    # auto
    if settings.openai_api_key or settings.google_api_key:
        return _pick_remote_client(http, settings)

    logger.warning("No OPENAI_API_KEY or GOOGLE_API_KEY; using mock LLM client (ANALYSIS_MODE=auto).")
    return MockLlmClient()
