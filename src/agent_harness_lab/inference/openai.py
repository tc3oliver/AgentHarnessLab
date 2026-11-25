from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agent_harness_lab.core.config import InferenceConfig
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.inference.base import EndpointInfo

_TIMEOUT_S = 15


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the API key to another host."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def api_key(config: InferenceConfig) -> str | None:
    if config.api_key_env is None:
        return None
    key = os.environ.get(config.api_key_env)
    if not key:
        raise ConfigError(f"environment variable {config.api_key_env} is not set")
    return key


def _get(url: str, key: str | None) -> Any:
    request = urllib.request.Request(url)  # noqa: S310 - the config only allows http(s)
    if key is not None:
        request.add_header("Authorization", f"Bearer {key}")
    with urllib.request.build_opener(_NoRedirect).open(request, timeout=_TIMEOUT_S) as response:
        return json.load(response)


class OpenAICompatibleBackend:
    def probe(self, config: InferenceConfig) -> EndpointInfo:
        if config.base_url is None:
            raise ConfigError("inference.base_url is required")
        key = api_key(config)
        base = config.base_url.rstrip("/")
        try:
            models = tuple(str(m["id"]) for m in _get(f"{base}/models", key)["data"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            # The exception may quote a response body; its type is enough and cannot leak the key.
            detail = f"HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
            raise RunError(f"cannot list models at {base}/models ({detail})") from None
        return EndpointInfo(models, self._engine_version(base, key) if config.backend == "vllm" else None)

    @staticmethod
    def _engine_version(base: str, key: str | None) -> str | None:
        """vLLM serves /version next to /v1. Absent behind most gateways."""
        parts = urlsplit(base)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path.removesuffix("/v1") + "/version", "", ""))
        try:
            version = _get(url, key)["version"]
        except (OSError, ValueError, KeyError, TypeError):
            return None
        return version if isinstance(version, str) else None
