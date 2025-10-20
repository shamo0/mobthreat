from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class AppRecord:
    platform: str
    title: str
    package: str
    developer: str
    icon_url: str
    raw: Dict[str, Any]                
    keyword: Optional[str] = None       

class BaseScanner:
    def fetch_by_keyword(self, keyword: str) -> List[AppRecord]:
        raise NotImplementedError

    def fetch_by_package(self, package: str) -> List[AppRecord]:
        raise NotImplementedError
