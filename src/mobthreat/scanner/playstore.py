from .base import BaseScanner, AppRecord
from typing import List
import logging

logger = logging.getLogger(__name__)

try:
    from google_play_scraper import search, app
except Exception as e:
    search = None
    app = None
    logger.warning("google_play_scraper not available; install google_play_scraper for Play Store support")


class PlayStoreScanner(BaseScanner):
    def fetch_by_keyword(self, keyword: str) -> List[AppRecord]:
        if search is None:
            raise RuntimeError("google_play_scraper not installed")
        results = search(keyword, lang="en", country="us", n_hits=50)
        out = []
        for r in results:
            rec = AppRecord(
                platform="android",
                title=r.get("title", ""),
                package=r.get("appId", ""),
                developer=r.get("developer", ""),
                icon_url=r.get("icon", ""),
                raw=r,
                keyword=keyword, 
            )
            out.append(rec)
        return out

    def fetch_by_package(self, package: str) -> List[AppRecord]:
        if app is None:
            raise RuntimeError("google_play_scraper not installed")
        info = app(package, lang="en", country="us")
        if not info:
            return []
        return [
            AppRecord(
                platform="android",
                title=info.get("title", ""),
                package=info.get("appId", ""),
                developer=info.get("developer", ""),
                icon_url=info.get("icon", ""),
                raw=info,
            )
        ]
