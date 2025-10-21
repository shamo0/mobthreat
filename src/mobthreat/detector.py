from dataclasses import dataclass
from typing import Optional
from .scanner.base import AppRecord
from rapidfuzz import fuzz
from PIL import Image
from .vision.ocr import extract_text_from_image
import imagehash
import requests
import io
import logging
import warnings

warnings.filterwarnings("ignore", message="Palette images with Transparency expressed in bytes")

logger = logging.getLogger(__name__)


@dataclass
class Match:
    candidate: AppRecord
    name_score: float
    developer_score: float
    description_score: float
    ocr_score: float
    package_match: bool
    icon_distance: Optional[int]
    overall_score: float


def fetch_image_as_hash(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        ph = imagehash.phash(img)
        return ph
    except Exception as e:
        logger.debug(f"Failed to fetch/hash image {url}: {e}")
        return None


def _get(thresholds, key, default=None):
    if isinstance(thresholds, dict):
        return thresholds.get(key, default)
    return getattr(thresholds, key, default)


def compare_apps(known_name: str, known_package: Optional[str], candidate: AppRecord, thresholds) -> Match:

    name_score = fuzz.token_sort_ratio(known_name, candidate.title)
    dev_score = fuzz.token_sort_ratio(known_name, candidate.developer)

    package_match = False
    if known_package and known_package.strip():
        package_match = (known_package.lower() == (candidate.package or "").lower())

    desc_score = 0
    desc = (candidate.raw.get("description") or "").lower()
    if desc:
        brand_keywords = _get(thresholds, "brand_keywords", [])
        if not brand_keywords and "name" in candidate.raw:
            brand_keywords = [candidate.raw["name"]]

        hits = [kw for kw in brand_keywords if kw.lower() in desc]
        if hits:
            desc_score = _get(thresholds, "description_bonus", 20)
            logger.debug(f"[DESC MATCH] '{candidate.title}' matched description keywords: {hits}")

    ocr_score = 0
    ocr_text = ""
    if candidate.icon_url:
        try:
            ocr_text = extract_text_from_image(candidate.icon_url)
            brand_keywords = _get(thresholds, "brand_keywords", [])
            for kw in brand_keywords:
                if kw.lower() in ocr_text.lower():
                    ocr_score = 100
                    logger.debug(f"[OCR MATCH] '{candidate.title}' icon contains '{kw}' via OCR")
                    break
        except Exception as e:
            logger.debug(f"OCR failed for {candidate.title}: {e}")

    icon_dist = None
    if candidate.icon_url:
        cand_hash = fetch_image_as_hash(candidate.icon_url)
        icon_dist = None  

    w_name = 0.6
    w_dev = 0.15
    w_pkg = 0.15
    w_icon = 0.05
    w_desc = _get(thresholds, "description_weight", 15) / 100.0
    w_ocr = _get(thresholds, "ocr_weight", 10) / 100.0

    overall = (
        name_score * w_name
        + dev_score * w_dev
        + (100 if package_match else 0) * w_pkg
        + desc_score * w_desc
        + ocr_score * w_ocr
    )
    overall = min(100.0, overall)

    return Match(
        candidate=candidate,
        name_score=name_score,
        developer_score=dev_score,
        description_score=desc_score,
        ocr_score=ocr_score,
        package_match=package_match,
        icon_distance=icon_dist,
        overall_score=overall,
    )


def is_suspicious(match: Match, thresholds) -> bool:
    """Determine if a match crosses the suspicion thresholds."""
    if _get(thresholds, "package_exact", False) and match.package_match:
        return True
    if match.overall_score >= _get(thresholds, "overall_score", 70):
        return True
    if (
        match.name_score >= _get(thresholds, "name_fuzzy", 75)
        and match.overall_score >= _get(thresholds, "overall_score", 70) * 0.8
    ):
        return True
    return False
