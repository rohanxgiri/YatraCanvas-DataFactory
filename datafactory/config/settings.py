import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    user_agent: str = "YatraCanvas-DataFactory/1.0 (contact: info@yatracanvas.org)"
    cache_ttl_seconds: int = 604800  # 7 days

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "staging"

    @property
    def curated_dir(self) -> Path:
        return self.data_dir / "curated"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def releases_dir(self) -> Path:
        return self.project_root / "releases"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"

    @property
    def config_dir(self) -> Path:
        return self.project_root / "config"

    @property
    def source_cache_dir(self) -> Path:
        return self.data_dir / "source_cache"

    def ensure_directories(self) -> None:
        for d in [
            self.data_dir,
            self.raw_dir,
            self.cache_dir,
            self.staging_dir,
            self.curated_dir,
            self.media_dir,
            self.releases_dir,
            self.reports_dir,
            self.config_dir,
            self.config_dir / "generated_cities",
            self.source_cache_dir,
            self.source_cache_dir / "geonames",
            self.source_cache_dir / "osm",
            self.source_cache_dir / "wikivoyage",
            self.source_cache_dir / "wikidata",
            self.source_cache_dir / "foursquare",
            self.source_cache_dir / "alltheplaces",
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def categories_config(self) -> Dict[str, Any]:
        return self.load_yaml("categories.yaml")

    @property
    def quality_config(self) -> Dict[str, Any]:
        return self.load_yaml("quality.yaml")

    @property
    def planning_defaults_config(self) -> Dict[str, Any]:
        return self.load_yaml("planning_defaults.yaml")

    @property
    def sources_config(self) -> Dict[str, Any]:
        return self.load_yaml("sources.yaml")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings
