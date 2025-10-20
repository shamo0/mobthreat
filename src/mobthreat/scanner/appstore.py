from .base import BaseScanner, AppRecord
from typing import List
import requests
import logging

logger = logging.getLogger(__name__)


class AppStoreScanner(BaseScanner):
    lookup_url = "https://itunes.apple.com/search"

    def fetch_by_keyword(self, keyword: str) -> List[AppRecord]:
        params = {"term": keyword, "entity": "software", "limit": 50}
        r = requests.get(self.lookup_url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        out: List[AppRecord] = []
        for item in data.get("results", []):
            bundle = item.get("bundleId") or item.get("trackId")
            icon = item.get("artworkUrl100") or item.get("artworkUrl60")
            rec = AppRecord(
                platform="ios",
                title=item.get("trackName", ""),
                package=str(bundle),
                developer=item.get("sellerName", ""),
                icon_url=icon,
                raw=item,
                keyword=keyword,  # ✅ track which keyword produced this
            )
            out.append(rec)
        return out

    def fetch_by_package(self, package: str) -> List[AppRecord]:
        return self.fetch_by_keyword(package)
