
"""
OCR / Unstructured Text Extraction and Matching
Version: 1.5.6

This module extracts any text found in front/side/top bottle images and stores it
as unstructured data.

OCR engines are optional:
1. pytesseract, if installed and the Tesseract binary is available.
2. easyocr, if installed.
3. fallback returns empty text with OCR unavailable status.

The rest of the application continues to work even if OCR is not installed.
"""

from __future__ import annotations

from typing import Dict, Optional, List
from pathlib import Path
import re
from difflib import SequenceMatcher

import cv2
import numpy as np
from runtime_config import enable_ocr


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> List[str]:
    return [t for t in _normalize_text(text).split() if len(t) >= 2]


def _preprocess_for_ocr(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # upscale small labels
    h, w = gray.shape[:2]
    if max(h, w) < 1400:
        gray = cv2.resize(gray, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 7, 45, 45)
    # adaptive threshold often helps printed labels
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 9
    )
    return thr


def _ocr_with_tesseract(img) -> Dict:
    try:
        import pytesseract
        processed = _preprocess_for_ocr(img)
        config = "--oem 3 --psm 6"
        text = pytesseract.image_to_string(processed, config=config)
        return {
            "engine": "pytesseract",
            "available": True,
            "text": text or "",
            "error": None,
        }
    except Exception as exc:
        return {
            "engine": "pytesseract",
            "available": False,
            "text": "",
            "error": str(exc),
        }


_easyocr_reader = None
_easyocr_error = None


def _ocr_with_easyocr(img) -> Dict:
    global _easyocr_reader, _easyocr_error
    try:
        if _easyocr_reader is None and _easyocr_error is None:
            import easyocr
            _easyocr_reader = easyocr.Reader(["en"], gpu=False)
        if _easyocr_reader is None:
            return {"engine": "easyocr", "available": False, "text": "", "error": _easyocr_error}
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = _easyocr_reader.readtext(rgb, detail=0, paragraph=True)
        return {
            "engine": "easyocr",
            "available": True,
            "text": " ".join(results or []),
            "error": None,
        }
    except Exception as exc:
        _easyocr_error = str(exc)
        return {
            "engine": "easyocr",
            "available": False,
            "text": "",
            "error": str(exc),
        }


def extract_text_from_image(path: Optional[str], view_name: str) -> Dict:
    if not path:
        return {
            "view": view_name,
            "engine": "none",
            "available": False,
            "raw_text": "",
            "normalized_text": "",
            "tokens": [],
            "token_count": 0,
            "error": "No image supplied",
        }

    img = cv2.imread(path)
    if img is None:
        return {
            "view": view_name,
            "engine": "none",
            "available": False,
            "raw_text": "",
            "normalized_text": "",
            "tokens": [],
            "token_count": 0,
            "error": "Could not read image",
        }

    result = _ocr_with_tesseract(img)
    if not result["available"]:
        result_easy = _ocr_with_easyocr(img)
        if result_easy["available"]:
            result = result_easy

    raw_text = result.get("text", "") or ""
    normalized = _normalize_text(raw_text)
    tokens = _tokens(raw_text)

    return {
        "view": view_name,
        "engine": result.get("engine", "none"),
        "available": bool(result.get("available")),
        "raw_text": raw_text.strip(),
        "normalized_text": normalized,
        "tokens": tokens,
        "token_count": len(tokens),
        "error": result.get("error"),
    }


def extract_text_from_images(front_path: Optional[str], side_path: Optional[str], top_path: Optional[str], force: bool = False) -> Dict:
    if not force and not enable_ocr():
        return {
            "views": {},
            "combined_raw_text": "",
            "combined_normalized_text": "",
            "combined_tokens": [],
            "combined_token_count": 0,
            "engine_status": {"any_available": False, "engines_used": [], "view_errors": {}, "disabled": True},
            "note": "OCR disabled. Set ENABLE_OCR=true to enable automatic text extraction, or use registration text analysis to force OCR for that request."
        }

    views = {
        "front": extract_text_from_image(front_path, "front"),
        "side": extract_text_from_image(side_path, "side"),
        "top": extract_text_from_image(top_path, "top"),
    }
    combined_raw = " ".join(v.get("raw_text", "") for v in views.values()).strip()
    combined_norm = _normalize_text(combined_raw)
    combined_tokens = _tokens(combined_raw)
    engine_status = {
        "any_available": any(v.get("available") for v in views.values()),
        "engines_used": sorted(set(v.get("engine") for v in views.values() if v.get("available"))),
        "view_errors": {k: v.get("error") for k, v in views.items() if v.get("error")},
    }
    return {
        "views": views,
        "combined_raw_text": combined_raw,
        "combined_normalized_text": combined_norm,
        "combined_tokens": combined_tokens,
        "combined_token_count": len(combined_tokens),
        "engine_status": engine_status,
    }


def compare_text_data(master_text: Dict, observed_text: Dict) -> Dict:
    master_norm = (master_text or {}).get("combined_normalized_text", "") or ""
    observed_norm = (observed_text or {}).get("combined_normalized_text", "") or ""

    master_tokens = set((master_text or {}).get("combined_tokens", []) or [])
    observed_tokens = set((observed_text or {}).get("combined_tokens", []) or [])

    if not master_norm and not observed_norm:
        return {
            "enabled": False,
            "passed": True,
            "text_match_percent": None,
            "sequence_similarity_percent": None,
            "token_similarity_percent": None,
            "reason": "No OCR text available on either registered or observed images",
            "matched_tokens": [],
            "missing_tokens": [],
            "new_tokens": [],
        }

    if not master_norm or not observed_norm:
        return {
            "enabled": True,
            "passed": False,
            "text_match_percent": 0.0,
            "sequence_similarity_percent": 0.0,
            "token_similarity_percent": 0.0,
            "reason": "OCR text present on only one side",
            "matched_tokens": sorted(master_tokens & observed_tokens),
            "missing_tokens": sorted(master_tokens - observed_tokens),
            "new_tokens": sorted(observed_tokens - master_tokens),
        }

    seq = SequenceMatcher(None, master_norm, observed_norm).ratio()
    union = master_tokens | observed_tokens
    inter = master_tokens & observed_tokens
    token_sim = len(inter) / len(union) if union else 0.0

    # Weighted similarity: tokens matter slightly more than character sequence.
    final = (token_sim * 0.60) + (seq * 0.40)
    passed = final >= 0.70

    return {
        "enabled": True,
        "passed": passed,
        "text_match_percent": round(final * 100, 2),
        "sequence_similarity_percent": round(seq * 100, 2),
        "token_similarity_percent": round(token_sim * 100, 2),
        "minimum_required_percent": 70,
        "reason": None if passed else "OCR text similarity below threshold",
        "matched_tokens": sorted(inter),
        "missing_tokens": sorted(master_tokens - observed_tokens),
        "new_tokens": sorted(observed_tokens - master_tokens),
        "master_text_preview": master_norm[:500],
        "observed_text_preview": observed_norm[:500],
    }


def ocr_status() -> Dict:
    if not enable_ocr():
        return {
            "ocr_layer_enabled": False,
            "available_engines": [],
            "errors": {},
            "note": "OCR is disabled for speed. Set ENABLE_OCR=true and install OCR dependencies to enable."
        }

    engines = []
    errors = {}
    try:
        import pytesseract
        engines.append("pytesseract_python_package")
        try:
            ver = str(pytesseract.get_tesseract_version())
            engines.append(f"tesseract_binary_{ver}")
        except Exception as exc:
            errors["tesseract_binary"] = str(exc)
    except Exception as exc:
        errors["pytesseract"] = str(exc)

    try:
        import easyocr
        engines.append("easyocr")
    except Exception as exc:
        errors["easyocr"] = str(exc)

    return {
        "ocr_layer_enabled": bool(engines),
        "available_engines": engines,
        "errors": errors,
        "note": "OCR is optional. Install backend/requirements_ocr.txt and Tesseract system binary for stronger OCR."
    }
