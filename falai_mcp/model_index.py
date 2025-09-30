from __future__ import annotations

import re
from functools import lru_cache
from importlib import resources
from typing import Iterable, List, Optional

import logging

logger = logging.getLogger(__name__)

_ENDPOINT_PATTERN = re.compile(r"\s*\"([^\"]+)\"\s*:\s*{")


def _iter_endpoint_lines(lines: Iterable[str]) -> Iterable[str]:
    for line in lines:
        match = _ENDPOINT_PATTERN.match(line)
        if match:
            yield match.group(1)


@lru_cache(maxsize=1)
def load_packaged_model_ids() -> Optional[List[str]]:
    """Parse fal-client endpoint definitions when bundled with the package.

    Newer releases of `fal-client` omit the TypeScript endpoint catalogue. When
    the resource is not present we return ``None`` so callers can fall back to a
    remote catalogue or other data source.
    """

    try:
        resource = resources.files("fal_client").joinpath("types/endpoints.d.ts")
    except ModuleNotFoundError:
        logger.debug("fal_client package is not installed; no packaged model catalogue available")
        return None

    try:
        with resource.open("r", encoding="utf-8") as fh:
            ids = sorted(set(_iter_endpoint_lines(fh)))
    except FileNotFoundError:
        logger.debug("fal_client no longer ships types/endpoints.d.ts; falling back to remote catalogue")
        return None

    return ids


def load_model_ids() -> List[str]:
    """Retained for backwards compatibility when the packaged catalogue exists."""

    packaged = load_packaged_model_ids()
    if packaged is None:
        raise FileNotFoundError("fal_client does not provide types/endpoints.d.ts")
    return packaged


def filter_models(
    allowed: Iterable[str] | None = None,
    catalogue: Iterable[str] | None = None,
) -> List[str]:
    if catalogue is None:
        packaged = load_packaged_model_ids()
        catalogue = packaged or []
    else:
        catalogue = list(catalogue)

    if not allowed:
        return list(catalogue)

    allowed_set = {model.strip() for model in allowed if model and model.strip()}
    return [model for model in catalogue if model in allowed_set]
