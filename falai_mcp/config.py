from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the fal.ai MCP server."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FALAI_", extra="ignore")

    fal_key: Optional[str] = Field(default=None, alias="FAL_KEY")
    fal_key_id: Optional[str] = Field(default=None, alias="FAL_KEY_ID")
    fal_key_secret: Optional[str] = Field(default=None, alias="FAL_KEY_SECRET")

    allowed_models: Optional[List[str]] = Field(default=None, alias="ALLOWED_MODELS")
    default_model_keywords: Optional[List[str]] = Field(
        default=None,
        alias="MODEL_KEYWORDS",
        description=(
            "Optional list of keywords used to scope search results when no"
            " explicit model list is supplied."
        ),
    )

    request_timeout: float = Field(default=120.0, alias="REQUEST_TIMEOUT")

    enable_http: bool = Field(default=False, alias="ENABLE_HTTP")
    http_host: str = Field(default="127.0.0.1", alias="HTTP_HOST")
    http_port: int = Field(default=8000, alias="HTTP_PORT")

    @property
    def api_key(self) -> Optional[str]:
        if self.fal_key:
            return self.fal_key
        if self.fal_key_id and self.fal_key_secret:
            return f"{self.fal_key_id}:{self.fal_key_secret}"
        return None

    @model_validator(mode="after")
    def _propagate_key_to_env(self) -> "Settings":
        """Ensure fal-client sees the resolved credentials."""

        if self.api_key and "FAL_KEY" not in os.environ:
            os.environ["FAL_KEY"] = self.api_key
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
