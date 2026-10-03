import os
from dataclasses import dataclass, field
from typing import Any
from dotenv import dotenv_values
from ..config.settings import get_settings


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"true", "1", "yes"}


@dataclass
class AIConfig:
    mode: str = "FREE_ONLY"
    enabled: bool = True
    providers: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)
    prompt_version: str = "1"
    credentials: dict[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls):
        settings = get_settings()
        # Never log this mapping. Process environment takes precedence over local .env.
        local = dotenv_values(settings.project_root / ".env", interpolate=False)
        def value(name, default=None):
            return os.environ.get(name, local.get(name) if local.get(name) is not None else default)
        def boolean(name, default=False):
            return str(value(name, str(default))).strip().lower() in {"true", "1", "yes"}
        raw = settings.load_yaml("ai.yaml")
        providers = raw.get("providers", {})
        for provider, cfg in providers.items():
            cfg = dict(cfg)
            cfg["model"] = value(f"{provider.upper()}_MODEL", cfg["model"])
            cfg["free_tier_confirmed"] = boolean(f"{provider.upper()}_FREE_TIER_CONFIRMED")
            providers[provider] = cfg
        limits = dict(raw.get("limits", {}))
        for env, key in [("AI_MAX_CALLS_PER_CITY", "calls"), ("AI_MAX_VISION_CALLS_PER_CITY", "vision_calls"), ("AI_MAX_ESCALATIONS_PER_CITY", "escalations")]:
            if value(env) is not None:
                limits[key] = max(0, int(value(env)))
        return cls(value("AI_MODE", "FREE_ONLY"), boolean("AI_ENABLED", True), providers, limits,
                   raw.get("prompt_version", "1"),
                   {p: value(f"{p.upper()}_API_KEY", "") for p in ("groq", "gemini")})

    def permitted(self, provider: str, model: str) -> bool:
        cfg = self.providers.get(provider, {})
        return (self.mode == "FREE_ONLY" and provider in {"groq", "gemini"}
                and model in cfg.get("free_models", []) and cfg.get("free_tier_confirmed") is True)
