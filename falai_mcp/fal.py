from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

import httpx
import fal_client

from .model_index import filter_models, load_model_ids

logger = logging.getLogger(__name__)


class FalAIService:
    """Thin wrapper around fal.ai HTTP APIs and fal-client helpers."""

    def __init__(self, api_key: Optional[str], timeout: float = 120.0):
        self.api_key = api_key
        self.timeout = timeout
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)
        self._client = fal_client.SyncClient(key=api_key, default_timeout=timeout)

    # ------------------------------------------------------------------
    # Model catalogue helpers
    def list_models(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        allowed: Iterable[str] | None = None,
    ) -> Dict[str, Any]:
        models = filter_models(allowed)

        if per_page and per_page > 0 and page and page > 0:
            start = (page - 1) * per_page
            end = start + per_page
            sliced = models[start:end]
            return {
                "page": page,
                "per_page": per_page,
                "total": len(models),
                "items": sliced,
            }
        return {"total": len(models), "items": models}

    def search_models(
        self,
        keywords: Iterable[str],
        allowed: Iterable[str] | None = None,
    ) -> List[str]:
        catalogue = filter_models(allowed) if allowed else load_model_ids()
        tokens = [token.strip().lower() for token in keywords if token.strip()]
        if not tokens:
            return catalogue
        results = [
            model
            for model in catalogue
            if all(token in model.lower() for token in tokens)
        ]
        return results

    # ------------------------------------------------------------------
    # Schema helpers
    def fetch_schema(self, model_id: str) -> Dict[str, Any]:
        url = f"https://fal.run/{model_id}/schema"
        response = self._http.get(url, headers=self._auth_headers)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Queue / run helpers
    def run(self, model_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._client.run(model_id, arguments=arguments)

    def submit(self, model_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handle = self._client.submit(model_id, arguments=arguments)
        return {
            "request_id": handle.request_id,
            "status_url": handle.status_url,
            "response_url": handle.response_url,
            "cancel_url": handle.cancel_url,
        }

    # ------------------------------------------------------------------
    # Queue URL helpers
    def fetch_json(self, url: str) -> Dict[str, Any]:
        response = self._http.get(url, headers=self._auth_headers)
        response.raise_for_status()
        return response.json()

    def put(self, url: str) -> Dict[str, Any]:
        response = self._http.put(url, headers=self._auth_headers)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {"status": "ok"}

    # ------------------------------------------------------------------
    # Storage helpers
    def upload_file(self, path: str) -> str:
        return self._client.upload_file(path)

    # ------------------------------------------------------------------
    @property
    def _auth_headers(self) -> Dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Key {self.api_key}"}
