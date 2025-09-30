from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Set
from weakref import WeakKeyDictionary

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.context import Context

from .config import get_settings
from .fal import FalAIService

logger = logging.getLogger(__name__)


@dataclass
class SessionOverrides:
    api_key: Optional[str] = None
    allowed_models: Optional[Set[str]] = None
    model_keywords: Optional[list[str]] = None


def build_server() -> FastMCP:
    settings = get_settings()

    @lru_cache(maxsize=16)
    def service_for(api_key: Optional[str]) -> FalAIService:
        return FalAIService(api_key=api_key, timeout=settings.request_timeout)

    default_service = service_for(settings.api_key)

    base_allowed = settings.allowed_models
    if not base_allowed and settings.default_model_keywords:
        base_allowed = default_service.search_models(settings.default_model_keywords)

    default_allowed_set: Optional[Set[str]] = set(base_allowed or []) or None

    session_overrides: WeakKeyDictionary[Any, SessionOverrides] = WeakKeyDictionary()

    def get_overrides(ctx: Context) -> SessionOverrides:
        session = ctx.session
        overrides = session_overrides.get(session)
        if overrides is None:
            overrides = SessionOverrides()
            session_overrides[session] = overrides
        return overrides

    def resolve_runtime(ctx: Context) -> tuple[FalAIService, Optional[Set[str]]]:
        overrides = get_overrides(ctx)
        api_key = overrides.api_key if overrides.api_key is not None else settings.api_key
        service = service_for(api_key)

        allowed: Optional[Set[str]] = default_allowed_set.copy() if default_allowed_set else None

        if overrides.allowed_models is not None:
            override_set = {model for model in overrides.allowed_models if model}
            if allowed is not None:
                allowed = override_set & allowed
            else:
                allowed = override_set
        elif overrides.model_keywords:
            keywords = [kw for kw in overrides.model_keywords if kw]
            base = allowed if allowed is not None else None
            allowed = set(service.search_models(keywords, allowed=base))

        return service, allowed

    def ensure_allowed(model_id: str, allowed: Optional[Set[str]]) -> None:
        if allowed is not None and model_id not in allowed:
            raise ToolError(f"Model '{model_id}' is not enabled on this session.")

    mcp = FastMCP(name="fal.ai")

    def _wrap_http(callable_):
        try:
            return callable_()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
            detail = exc.response.text
            raise ToolError(
                f"fal.ai request failed with status {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network dependent
            raise ToolError(f"fal.ai request failed: {exc}") from exc

    @mcp.tool(description="Configure fal.ai credentials and allowed models for this session")
    def configure(
        ctx: Context,
        api_key: Optional[str] = None,
        allowed_models: Optional[list[str]] = None,
        model_keywords: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        overrides = get_overrides(ctx)

        if api_key is not None:
            overrides.api_key = api_key or None

        if allowed_models is not None:
            cleaned = {model.strip() for model in allowed_models if model and model.strip()}
            overrides.allowed_models = cleaned if cleaned else None

        if model_keywords is not None:
            cleaned_keywords = [kw.strip() for kw in model_keywords if kw and kw.strip()]
            overrides.model_keywords = cleaned_keywords or None

        _, allowed = resolve_runtime(ctx)
        return {
            "api_key": overrides.api_key or settings.api_key,
            "allowed_models": sorted(allowed) if allowed is not None else None,
        }

    @mcp.tool(description="List available fal.ai model identifiers")
    def models(ctx: Context, page: Optional[int] = None, total: Optional[int] = None) -> Dict[str, Any]:
        service, allowed = resolve_runtime(ctx)
        return service.list_models(page=page, per_page=total, allowed=allowed)

    @mcp.tool(description="Search for fal.ai models by keyword")
    def search(ctx: Context, keywords: str) -> Dict[str, Any]:
        tokens = [token for token in keywords.split() if token.strip()]
        if not tokens:
            raise ToolError("Provide at least one keyword to search")
        service, allowed = resolve_runtime(ctx)
        results = service.search_models(tokens, allowed=allowed)
        return {"keywords": tokens, "items": results}

    @mcp.tool(description="Retrieve the OpenAPI schema for a fal.ai model")
    def schema(ctx: Context, model_id: str) -> Dict[str, Any]:
        service, allowed = resolve_runtime(ctx)
        ensure_allowed(model_id, allowed)
        return _wrap_http(lambda: service.fetch_schema(model_id))

    @mcp.tool(description="Generate content using a fal.ai model")
    def generate(
        ctx: Context,
        model: str,
        parameters: Dict[str, Any],
        queue: bool = False,
    ) -> Dict[str, Any]:
        service, allowed = resolve_runtime(ctx)
        ensure_allowed(model, allowed)
        if not isinstance(parameters, dict):
            raise ToolError("parameters must be a JSON object")
        if queue:
            return _wrap_http(lambda: service.submit(model, parameters))
        return _wrap_http(lambda: service.run(model, parameters))

    @mcp.tool(description="Get the result from a queued fal.ai request")
    def result(ctx: Context, url: str) -> Dict[str, Any]:
        service, _ = resolve_runtime(ctx)
        return _wrap_http(lambda: service.fetch_json(url))

    @mcp.tool(description="Check the status of a queued fal.ai request")
    def status(ctx: Context, url: str) -> Dict[str, Any]:
        service, _ = resolve_runtime(ctx)
        return _wrap_http(lambda: service.fetch_json(url))

    @mcp.tool(description="Cancel a queued fal.ai request")
    def cancel(ctx: Context, url: str) -> Dict[str, Any]:
        service, _ = resolve_runtime(ctx)
        return _wrap_http(lambda: service.put(url))

    @mcp.tool(description="Upload a file to fal.ai CDN and return the access URL")
    def upload(ctx: Context, path: str) -> Dict[str, Any]:
        service, _ = resolve_runtime(ctx)
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise ToolError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ToolError(f"Path is not a file: {file_path}")
        url = service.upload_file(str(file_path))
        return {"url": url}

    return mcp


_server: Optional[FastMCP] = None


def get_server() -> FastMCP:
    global _server
    if _server is None:
        _server = build_server()
    return _server
