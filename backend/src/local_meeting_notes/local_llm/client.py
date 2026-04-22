"""Local LLM client implementation for Ollama-compatible runtimes."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ..config import AppConfig


class LocalLlmClientError(RuntimeError):
    """Raised when the local LLM runtime cannot satisfy a request."""


@dataclass(slots=True)
class OllamaClient:
    base_url: str
    model_name: str
    timeout_seconds: int

    def check(self) -> dict[str, Any]:
        response = self._request("GET", "/api/tags")
        models = response.get("models", [])
        return {"status": "ok", "base_url": self.base_url, "model_name": self.model_name, "models": models}

    def generate_json(self, prompt: str) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/api/generate",
            {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
        )
        raw_payload = response.get("response")
        if not isinstance(raw_payload, str) or not raw_payload.strip():
            raise LocalLlmClientError("Local LLM returned an empty JSON payload.")

        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise LocalLlmClientError(f"Local LLM returned invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LocalLlmClientError("Local LLM JSON payload must be an object.")
        return parsed

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(
            url=f"{self.base_url.rstrip('/')}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                content = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LocalLlmClientError(
                f"Local LLM HTTP error {exc.code}: {details or exc.reason}"
            ) from exc
        except error.URLError as exc:
            raise LocalLlmClientError(f"Local LLM connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LocalLlmClientError("Local LLM request timed out.") from exc
        except socket.timeout as exc:
            raise LocalLlmClientError("Local LLM request timed out.") from exc

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LocalLlmClientError(f"Local runtime returned non-JSON content: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LocalLlmClientError("Local runtime response must be a JSON object.")
        return parsed


def build_local_llm_client(config: AppConfig) -> OllamaClient:
    return OllamaClient(
        base_url=config.local_llm_base_url,
        model_name=config.local_llm_model,
        timeout_seconds=config.local_llm_timeout_seconds,
    )
