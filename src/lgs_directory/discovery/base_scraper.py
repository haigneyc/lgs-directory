"""Base scraper infrastructure — shared httpx client, cache I/O, rate limiting."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Self, TypeVar

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_DEFAULT_TIMEOUT = 30.0


class BaseScraper:
    """Shared infrastructure for all discovery scrapers.

    Handles httpx client lifecycle, rate limiting delay config,
    and close semantics. Subclasses implement fetch_stores().
    """

    def __init__(
        self,
        delay: float,
        headers: dict[str, str],
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        assert delay >= 0, "Delay must be non-negative"
        assert isinstance(headers, dict), "headers must be a dict"
        self._delay = delay
        self._headers = headers
        self._timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Return a cached httpx client, creating one if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                headers=self._headers,
                timeout=self._timeout,
            )
        assert self._client is not None
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __del__(self) -> None:
        if self._client is not None and not self._client.is_closed:
            logger.warning(
                "%s was garbage-collected with an open httpx client. "
                "Use a context manager or call close() explicitly.",
                type(self).__name__,
            )


def save_to_cache(stores: list[Any], path: Path, label: str = "stores") -> None:
    """Save a list of Pydantic models to a JSON cache file.

    Args:
        stores: List of Pydantic BaseModel instances.
        path: File path to write JSON to.
        label: Human-readable label for log messages.
    """
    assert isinstance(path, Path), "path must be a Path"
    assert isinstance(stores, list), "stores must be a list"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [s.model_dump() for s in stores]
    path.write_text(json.dumps(data, indent=2))
    assert path.exists()
    logger.info("Saved %d %s to %s", len(data), label, path)


def load_from_cache(
    path: Path,
    model_class: type[T],
    label: str = "stores",
) -> list[T]:
    """Load a list of Pydantic models from a JSON cache file.

    Args:
        path: File path to read JSON from.
        model_class: Pydantic model class for validation.
        label: Human-readable label for log messages.

    Returns:
        Validated list of model instances.
    """
    assert isinstance(path, Path), "path must be a Path"
    assert path.exists(), f"Cache file not found: {path}"
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Cache data must be a list"
    stores = [model_class.model_validate(item) for item in data]
    logger.info("Loaded %d %s from %s", len(stores), label, path)
    return stores
