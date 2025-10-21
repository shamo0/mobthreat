import pytesseract
from PIL import Image
import requests, io, logging

logger = logging.getLogger(__name__)

def extract_text_from_image(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        text = pytesseract.image_to_string(img, lang="eng")
        text = text.strip()
        if text:
            logger.debug(f"[OCR] Extracted text from {url[:40]}...: {text[:50]}")
        return text
    except Exception as e:
        logger.debug(f"[OCR ERROR] {url}: {e}")
        return ""
