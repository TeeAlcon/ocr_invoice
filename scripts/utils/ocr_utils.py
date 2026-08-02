import os
from pathlib import Path

from PIL import Image
import pymupdf
import numpy as np

_ocr_instance = None

def _get_paddleocr():
    """Lazy import PaddleOCR to avoid initialization on module import."""
    # Import inside function to avoid loading unless needed
    from paddleocr import PaddleOCR
    return PaddleOCR

def create_ocr():
    """Create and return a singleton PaddleOCR instance."""
    MODEL_BASE = Path(__file__).parent.parent / "models"
    global _ocr_instance
    if _ocr_instance is None:
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        PaddleOCR = _get_paddleocr()
        _ocr_instance = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            text_detection_model_dir=str(MODEL_BASE / "PP-OCRv5_mobile_det_infer"),
            text_recognition_model_dir=str(MODEL_BASE / "en_PP-OCRv5_mobile_rec_infer"),
            text_recognition_model_name="en_PP-OCRv5_mobile_rec",
            text_detection_model_name="PP-OCRv5_mobile_det",
        )
    return _ocr_instance

def numpy_ocr(image_np, ocr):
    """Run OCR on a NumPy image array and return recognized text strings."""
    result = ocr.predict(input=image_np)
    texts = []
    for res in result:
        texts.extend(res.get("rec_texts", []))
    return texts

def _rect_to_rgb(page, rect, dpi):
    """Render PDF rectangle as RGB numpy array."""
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False, colorspace=pymupdf.csRGB)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

def og_extract_text_or_ocr(page, rect, ocr, dpi=150):
    if text := page.get_text("text", clip=rect).strip():
        return " ".join(text.split())
    return " ".join(numpy_ocr(_rect_to_rgb(page, rect, dpi), ocr))

def extract_text_or_ocr(page, rect, ocr, dpi=150):
    if text := page.get_text("text", clip=rect).strip():
        return " ".join(text.split())

    if page.get_text("text").strip():
        return ""

    return " ".join(numpy_ocr(_rect_to_rgb(page, rect, dpi), ocr))


def ocr_rotated_rect(page, rect, ocr, dpi=300, rotate=90):
    image_np = _rect_to_rgb(page, rect, dpi)

    if rotate:
        image_np = np.array(
            Image.fromarray(image_np).rotate(rotate, expand=True)
        )

    return " ".join(numpy_ocr(image_np, ocr))