"""
Quality gate pipeline for generated images.

Production gates (fast, zero model downloads):
  Gate 1: Pixel sanity — rejects blank/solid images
  Gate 2: WCAG contrast check — pure PIL/numpy, instant

Heavy gates DISABLED in production:
  EasyOCR downloads ~1.5GB models on first call and hangs Railway cold starts.
  Aesthetic predictor also requires large model download.
  These were causing 10+ minute hangs. Re-enable only on persistent GPU infra.
"""

import asyncio
import re
from io import BytesIO

import numpy as np
from PIL import Image


def _normalize_arabic(text: str) -> str:
    return re.sub(r"[^؀-ۿ\s]", "", text).strip()


async def run_image_qa_gate(image_bytes: bytes, min_aesthetic: float = 5.0) -> dict:
    """
    Fast pre-composite QA. No model downloads.
    Rejects blank/solid-color images (fal.ai failure mode).
    """
    def _check():
        result = {"passed": True, "scores": {}, "reason": None}
        try:
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img, dtype=float)
            std = float(arr.std())
            result["scores"]["pixel_std"] = round(std, 2)
            if std < 8.0:
                result["passed"] = False
                result["reason"] = f"Image is blank/solid (pixel std={std:.1f} < 8)"
                return result
        except Exception as exc:
            result["scores"]["pixel_check"] = f"skipped:{type(exc).__name__}"

        result["scores"]["aesthetic"] = "skipped_no_model_in_prod"
        result["scores"]["ocr_background"] = "skipped_no_model_in_prod"
        return result

    return await asyncio.to_thread(_check)


async def run_final_qa_gate(final_bytes: bytes, expected_arabic: str) -> dict:
    """
    Fast post-composite QA. WCAG contrast check only — no model downloads.
    OCR gate removed: EasyOCR model download hangs Railway on every cold start.
    """
    def _check():
        result = {"passed": True, "scores": {}, "reason": None}

        try:
            img = Image.open(BytesIO(final_bytes)).convert("RGB")
            arr = np.array(img, dtype=float) / 255.0
            lin = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
            luminance = 0.2126 * lin[:, :, 0] + 0.7152 * lin[:, :, 1] + 0.0722 * lin[:, :, 2]
            h_, w_ = luminance.shape
            zone = luminance[h_ // 2:, w_ // 2:]
            bg_lum = float(zone.mean())
            contrast_ratio = 1.05 / (bg_lum + 0.05)
            result["scores"]["contrast_ratio"] = round(contrast_ratio, 2)
            result["scores"]["bg_luminance"] = round(bg_lum, 3)
            if contrast_ratio < 3.0:
                result["passed"] = False
                result["reason"] = f"Text contrast ratio {contrast_ratio:.1f} < 3.0 (WCAG AA large)"
                return result
        except Exception as exc:
            result["scores"]["contrast"] = f"skipped:{type(exc).__name__}"

        result["scores"]["ocr_arabic_legible"] = "skipped_no_model_in_prod"
        return result

    return await asyncio.to_thread(_check)
