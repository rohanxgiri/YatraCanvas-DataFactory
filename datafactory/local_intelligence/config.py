from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        def repository_config():
            from ..config.settings import get_settings
            return get_settings().load_yaml("local_media.yaml")
        return init_settings, env_settings, dotenv_settings, repository_config, file_secret_settings
    local_media_enabled: bool = True
    local_media_model: str = "google/siglip-base-patch16-224"
    local_media_revision: str = "main"
    local_media_batch_size: int = Field(default=4, ge=1, le=16)
    local_media_max_candidates: int = Field(default=20, ge=1, le=100)
    local_media_thumbnail_size: int = Field(default=384, ge=224, le=1024)
    local_media_allow_download: bool = False
    local_media_device: str = "cpu"
    local_media_model_cache: Path | None = None
    local_media_cpu_threads: int = Field(default=4, ge=1, le=32)
    # Unset until calibrated on actual images; never infer identity from a score.
    local_media_min_relevance: float | None = Field(default=None, ge=0, le=1)
    local_media_relevance_threshold: float | None = Field(default=None, ge=0, le=1)
    local_media_ambiguity_margin: float | None = Field(default=None, ge=0, le=1)
    local_media_calibration_model: str | None = None
    local_media_calibration_revision: str | None = None
    local_media_high_threshold: float = Field(default=.85, ge=0, le=1)
    local_media_label_margin: float = Field(default=.20, ge=0, le=1)
    local_text_enabled: bool = False
    local_text_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    local_text_allow_download: bool = False
    local_duplicate_threshold: int = Field(default=3, ge=0, le=6)
    hours_validator_backend: str = "python"
    hours_research_max_age_days: int = Field(default=180, ge=1)
