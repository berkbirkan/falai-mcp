from __future__ import annotations

import re
from functools import lru_cache
from importlib import resources
from typing import Iterable, List

_ENDPOINT_PATTERN = re.compile(r"\s*\"([^\"]+)\"\s*:\s*{")


def _iter_endpoint_lines(lines: Iterable[str]) -> Iterable[str]:
    for line in lines:
        match = _ENDPOINT_PATTERN.match(line)
        if match:
            yield match.group(1)


@lru_cache(maxsize=1)
def load_model_ids() -> List[str]:
    """Parse fal-client endpoint definitions to discover available model IDs."""

    with resources.files("fal_client").joinpath("types/endpoints.d.ts").open("r", encoding="utf-8") as fh:
        ids = sorted(set(_iter_endpoint_lines(fh)))
    return ids


def filter_models(allowed: Iterable[str] | None = None) -> List[str]:
    catalogue = load_model_ids()
    if not allowed:
        return catalogue
    allowed_set = {model.strip() for model in allowed if model.strip()}
    return [model for model in catalogue if model in allowed_set]
