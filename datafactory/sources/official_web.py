from typing import Optional
import httpx
from ..config.settings import get_settings


class OfficialWebValidator:
    def __init__(self):
        self.settings = get_settings()

    def validate_url(self, url: Optional[str]) -> Optional[str]:
        """Validate and clean URL string."""
        if not url:
            return None
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return url
