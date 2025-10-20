from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import yaml
import logging

logger = logging.getLogger(__name__)

@dataclass
class Thresholds:
    name_fuzzy: int
    package_exact: bool
    icon_phash_distance: int
    overall_score: int

@dataclass
class NotificationConfig:
    slack_webhook: Optional[str]
    discord_webhook: Optional[str]
    extra_recipients: List[str]

@dataclass
class TargetApp:
    name: str
    platform: str  # android | ios
    package: Optional[str] = None
    bundle: Optional[str] = None

@dataclass
class Target:
    id: str
    company_name: str
    keywords: List[str]
    known_apps: List[TargetApp]

@dataclass
class Config:
    poll_interval_minutes: int
    thresholds: Thresholds
    targets: List[Target]
    notifications: NotificationConfig
    logging: Dict[str, Any]

def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    t = data.get("thresholds", {})
    thresholds = Thresholds(
        name_fuzzy=t.get("name_fuzzy", 75),
        package_exact=t.get("package_exact", True),
        icon_phash_distance=t.get("icon_phash_distance", 8),
        overall_score=t.get("overall_score", 70),
    )

    targets = []
    for x in data.get("targets", []):
        known_apps = []
        for ka in x.get("known_apps", []):
            known_apps.append(TargetApp(
                name=ka.get("name"),
                platform=ka.get("platform"),
                package=ka.get("package"),
                bundle=ka.get("bundle"),
            ))
        targets.append(Target(
            id=x["id"],
            company_name=x["company_name"],
            keywords=x.get("keywords", []),
            known_apps=known_apps,
        ))

    notifications = NotificationConfig(
        slack_webhook=data.get("notifications", {}).get("slack_webhook"),
        discord_webhook=data.get("notifications", {}).get("discord_webhook"),
        extra_recipients=data.get("notifications", {}).get("extra_recipients", []),
    )

    return Config(
        poll_interval_minutes=int(data.get("poll_interval_minutes", 60)),
        thresholds=thresholds,
        targets=targets,
        notifications=notifications,
        logging=data.get("logging", {"level": "INFO"}),
    )
