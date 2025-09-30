from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx
import fal_client

from .model_index import filter_models, load_packaged_model_ids

logger = logging.getLogger(__name__)

_PUBLIC_API_BASE = "https://fal.ai/api"


class FalAIService:
    """Thin wrapper around fal.ai HTTP APIs and fal-client helpers."""

    def __init__(self, api_key: Optional[str], timeout: float = 120.0):
        self.api_key = api_key
        self.timeout = timeout
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)
        self._client = fal_client.SyncClient(key=api_key, default_timeout=timeout)
        self._catalogue: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # Model catalogue helpers
    def list_models(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        allowed: Iterable[str] | None = None,
    ) -> Dict[str, Any]:
        catalogue = self._get_catalogue()
        models = filter_models(allowed, catalogue)

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
        catalogue = self._get_catalogue()
        if allowed:
            catalogue = filter_models(allowed, catalogue)
        tokens = [token.strip().lower() for token in keywords if token.strip()]
        if not tokens:
            return catalogue
        results = [
            model
            for model in catalogue
            if all(token in model.lower() for token in tokens)
        ]
        return results

    def _get_catalogue(self) -> List[str]:
        if self._catalogue is None:
            packaged = load_packaged_model_ids()
            if packaged is not None:
                self._catalogue = packaged
            else:
                self._catalogue = self._fetch_catalogue_from_public_api()
        return self._catalogue

    def _fetch_catalogue_from_public_api(self) -> List[str]:
        url = f"{_PUBLIC_API_BASE}/models"
        page = 1
        per_page = 200
        seen: List[str] = []
        seen_set: set[str] = set()

        while page <= 100:  # guard against runaway pagination
            try:
                response = self._http.get(
                    url,
                    params={"page": page, "total": per_page},
                    headers=self._auth_headers,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:  # pragma: no cover - network dependent
                logger.warning("Failed to fetch fal.ai model catalogue (page %s): %s", page, exc)
                break

            payload = response.json()
            batch = self._extract_model_ids(payload)
            if not batch:
                break

            new_items = [item for item in batch if item not in seen_set]
            if not new_items:
                break

            seen.extend(new_items)
            seen_set.update(new_items)

            if len(batch) < per_page:
                break

            page += 1

        if not seen:
            logger.warning("fal.ai model catalogue fetch returned no items; search results may be empty")

        return sorted(seen)

    @staticmethod
    def _extract_model_ids(payload: Any) -> List[str]:
        def coerce(item: Any) -> Optional[str]:
            if isinstance(item, str):
                value = item.strip()
                return value or None
            if isinstance(item, dict):
                for key in (
                    "id",
                    "endpoint_id",
                    "endpointId",
                    "model_id",
                    "modelId",
                    "slug",
                    "name",
                ):
                    candidate = item.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
            return None

        items: Sequence[Any]
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            raw_items = payload.get("items")
            if isinstance(raw_items, list):
                items = raw_items
            else:
                items = [payload]
        else:
            return []

        results: List[str] = []
        for item in items:
            value = coerce(item)
            if value:
                results.append(value)
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
