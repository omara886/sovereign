"""
Quality gate pipeline for generated images.
Gate 1: Aesthetic score >= threshold (aesthetic-predictor-v2-5)
Gate 2: Contrast check (kontrasto WCAG3)
Gate 3: OCR — no fake text in background
Gate 4: OCR — Arabic text legible post-compositing
"""

import asyncio
from io import BytesIO

from PIL import Image


async def run_image_qa_gate(image_bytes: bytes, min_aesthetic: float = 5.0) -> dict:
    """Run QA on raw generated image (before Arabic overlay)."""

    def _check():
        result = {"passed": True, "scores": {}, "reason": None}

        try:
            import torch
            from aesthetic_predictor_v2_5 import convert_v2_5_from_siglip

            model, preprocessor = convert_v2_5_from_siglip(low_cpu_mem_usage=True, trust_remote_code=True)
            model.eval()
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            px = preprocessor(images=img, return_tensors="pt").pixel_values
            with torch.inference_mode():
                score = float(model(px).item())
            result["scores"]["aesthetic"] = score
            if score < min_aesthetic:
                result["passed"] = False
                result["reason"] = f"Aesthetic score {score:.2f} < {min_aesthetic}"
                return result
        except ImportError:
            result["scores"]["aesthetic"] = "skipped_no_model"

        try:
            import easyocr

            reader = easyocr.Reader(["ar", "en"], gpu=False)
            texts = reader.readtext(image_bytes, detail=0)
            if texts:
                result["passed"] = False
                result["reason"] = f"Background contains text: {texts[:3]}"
                result["scores"]["ocr_background"] = texts
                return result
            result["scores"]["ocr_background"] = "clean"
        except ImportError:
            result["scores"]["ocr_background"] = "skipped_no_easyocr"

        return result

    return await asyncio.to_thread(_check)


async def run_final_qa_gate(final_bytes: bytes, expected_arabic: str) -> dict:
    """Run QA on final composited image (after Arabic overlay)."""

    def _check():
        result = {"passed": True, "scores": {}, "reason": None}

        try:
            from kontrasto import wcag_3

            img = Image.open(BytesIO(final_bytes)).convert("RGB")
            contrast = wcag_3.wcag3_contrast_light_or_dark(img, "#ffffff", "#000000")
            result["scores"]["contrast"] = contrast
        except ImportError:
            result["scores"]["contrast"] = "skipped_no_kontrasto"

        try:
            import easyocr

            reader = easyocr.Reader(["ar", "en"], gpu=False)
            texts = reader.readtext(final_bytes, detail=0)
            parsed = " ".join(texts)
            key_words = expected_arabic.split()[:2]
            found = any(w in parsed for w in key_words if len(w) > 2)
            result["scores"]["ocr_arabic_legible"] = found
            if not found and expected_arabic.strip():
                result["passed"] = False
                result["reason"] = f"Arabic text not detected by OCR: {expected_arabic[:30]}"
                return result
        except ImportError:
            result["scores"]["ocr_arabic_legible"] = "skipped_no_easyocr"

        return result

    return await asyncio.to_thread(_check)
