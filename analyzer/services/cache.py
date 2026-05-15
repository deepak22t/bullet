from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from analyzer.config import Settings
from analyzer.schemas.analysis import AnalysisResponse

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: redis.Redis | None = None
        if settings.redis_url:
            self.client = redis.from_url(settings.redis_url, decode_responses=True)

    async def get_analysis(self, payload: dict[str, Any]) -> AnalysisResponse | None:
        if not self.client:
            return None

        key = self._generate_key(payload)
        try:
            data = await self.client.get(key)
            if data:
                logger.info("cache hit for key=%s", key)
                return AnalysisResponse.model_validate_json(data)
        except Exception as e:
            logger.warning("cache get failed: %s", e)
        return None

    async def set_analysis(self, payload: dict[str, Any], response: AnalysisResponse) -> None:
        if not self.client:
            return

        key = self._generate_key(payload)
        try:
            # Don't cache partial/mock responses
            if response.meta.partial:
                return
            await self.client.set(
                key,
                response.model_dump_json(),
                ex=self.settings.redis_ttl_seconds,
            )
            logger.info("cache set for key=%s", key)
        except Exception as e:
            logger.warning("cache set failed: %s", e)

    def _generate_key(self, payload: dict[str, Any]) -> str:
        dump = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(dump.encode()).hexdigest()
        return f"analysis:{h}"

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
