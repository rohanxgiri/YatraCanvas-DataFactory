"""Vendor HTTP is confined here; exceptions contain codes, never request URLs/keys."""
import base64
import json
import os
import time
from typing import Protocol
import httpx
from .config import AIConfig


class AIError(Exception):
    def __init__(self, code: str, retry_after: float = 0):
        super().__init__(code)
        self.code, self.retry_after = code, retry_after


class AIProvider(Protocol):
    provider_id: str
    model: str
    def analyze_json(self, prompt: str, schema: dict) -> dict: ...
    def analyze_images(self, prompt: str, schema: dict, images: list[bytes]) -> dict: ...
    def extract_structured(self, prompt: str, schema: dict) -> dict: ...
    def health_check(self) -> dict: ...


class HTTPProvider:
    provider_id = ""

    def __init__(self, config: AIConfig, transport=None):
        self.config = config
        self.cfg = config.providers[self.provider_id]
        self.model = self.cfg["model"]
        self.key = os.getenv(f"{self.provider_id.upper()}_API_KEY", config.credentials.get(self.provider_id, ""))
        self.transport = transport
        self.verified = False
        self.last_call = 0.0

    def _request(self, method: str, path: str, payload=None):
        approved_endpoint = {"groq":"https://api.groq.com/openai/v1",
                             "gemini":"https://generativelanguage.googleapis.com/v1beta"}.get(self.provider_id)
        if self.cfg["endpoint"] != approved_endpoint:
            raise AIError("FREE_ONLY_BLOCKED")
        if not self.key:
            raise AIError("AI_UNAVAILABLE")
        if method != "GET" and (not self.config.enabled or not self.config.permitted(self.provider_id, self.model) or not self.verified):
            raise AIError("FREE_ONLY_BLOCKED")
        headers = ({"Authorization": f"Bearer {self.key}"} if self.provider_id == "groq"
                   else {"x-goog-api-key": self.key})
        try:
            with httpx.Client(timeout=self.config.limits.get("timeout_seconds", 25), transport=self.transport) as client:
                response = client.request(method, self.cfg["endpoint"] + path, headers=headers, json=payload)
            if response.status_code == 429:
                try:
                    delay = float(response.headers.get("retry-after", "1"))
                except ValueError:
                    delay = 1
                raise AIError("AI_QUOTA_DEFERRED", max(0, delay))
            if response.status_code in (401, 403, 404):
                raise AIError("AI_UNAVAILABLE")
            if response.status_code in (502, 503, 504):
                raise AIError("AI_UNAVAILABLE")
            if response.status_code != 200:
                raise AIError("AI_HTTP_ERROR")
            data = response.json()
            if not isinstance(data, dict):
                raise AIError("AI_RESULT_INVALID")
            return data
        except httpx.TimeoutException:
            raise AIError("AI_TIMEOUT") from None
        except (httpx.HTTPError, ValueError):
            raise AIError("AI_RESULT_INVALID") from None

    def health_check(self) -> dict:
        result = {"provider": self.provider_id, "key": "configured" if self.key else "missing", "model": self.model, "health": "AI_UNAVAILABLE"}
        if not self.config.enabled:
            return {**result, "health": "AI_DISABLED"}
        if not self.key:
            return result
        if not self.config.permitted(self.provider_id, self.model):
            return {**result, "health": "FREE_ONLY_BLOCKED"}
        try:
            data = self._request("GET", "/models")
            models = (data.get("data", []) if self.provider_id == "groq" else data.get("models", []))
            available = {m.get("id") if self.provider_id == "groq" else m.get("name", "").removeprefix("models/") for m in models}
            compatible = {m.get("name", "").removeprefix("models/") for m in models if "generateContent" in m.get("supportedGenerationMethods", [])} if self.provider_id == "gemini" else available
            for model in [self.model] + self.cfg.get("fallback_models", []):
                if model in available and model in compatible and self.config.permitted(self.provider_id, model):
                    self.model, self.verified = model, True
                    return {**result, "model": model, "health": "OK"}
            return {**result, "health": "MODEL_UNAVAILABLE"}
        except AIError as exc:
            return {**result, "health": exc.code}

    def _gate(self, images):
        if not self.config.enabled or not self.config.permitted(self.provider_id, self.model):
            raise AIError("FREE_ONLY_BLOCKED")
        if not self.verified and self.health_check()["health"] != "OK":
            raise AIError("AI_UNAVAILABLE")
        if len(images) > self.cfg.get("max_images", 3):
            raise AIError("AI_IMAGE_LIMIT")
        if sum(len(i) for i in images) > 12_000_000:
            raise AIError("AI_IMAGE_LIMIT")
        delay = self.config.limits.get("min_call_interval_seconds", 3) - (time.monotonic() - self.last_call)
        if delay > 0:
            time.sleep(delay)
        self.last_call = time.monotonic()

    def analyze_json(self, prompt: str, schema: dict) -> dict:
        return self.analyze_images(prompt, schema, [])

    def extract_structured(self, prompt: str, schema: dict) -> dict:
        return self.analyze_json(prompt, schema)


class GroqProvider(HTTPProvider):
    provider_id = "groq"

    def analyze_images(self, prompt: str, schema: dict, images: list[bytes]) -> dict:
        self._gate(images)
        content = [{"type": "text", "text": prompt + "\nReturn only JSON matching: " + json.dumps(schema)}]
        content += [{"type": "image_url", "image_url": {"url": "data:image/webp;base64," + base64.b64encode(i).decode()}} for i in images]
        data = self._request("POST", "/chat/completions", {
            "model": self.model, "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"}, "max_completion_tokens": 1500,
        })
        try:
            return json.loads(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise AIError("AI_RESULT_INVALID") from None


class GeminiProvider(HTTPProvider):
    provider_id = "gemini"

    def analyze_images(self, prompt: str, schema: dict, images: list[bytes]) -> dict:
        self._gate(images)
        parts = [{"text": prompt + "\nReturn only JSON matching: " + json.dumps(schema)}]
        parts += [{"inlineData": {"mimeType": "image/webp", "data": base64.b64encode(i).decode()}} for i in images]
        data = self._request("POST", f"/models/{self.model}:generateContent", {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 2000},
        })
        try:
            return json.loads("".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]))
        except (KeyError, IndexError, TypeError, ValueError):
            raise AIError("AI_RESULT_INVALID") from None
