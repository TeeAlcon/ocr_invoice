#!/usr/bin/env -S uv run

from ocr_utils import extract_text_or_ocr, create_ocr
import pymupdf
from pathlib import Path

def print_rect_text(pdf_path, rect, page):
    ocr = create_ocr()
    with pymupdf.open(pdf_path) as doc:
        text = extract_text_or_ocr(doc[page - 1], rect, ocr)
    print(text)
    return text

if __name__ == "__main__":    
    pdf_path = Path.cwd() / "outputs" / "6090066957_output" / "other.pdf"
    print("cwd:", Path.cwd())
    print("exists:", pdf_path.exists())
    print(pdf_path)

    page = 1
    print_rect_text(pdf_path, pymupdf.Rect(130, 0, 480, 110), page)
    print_rect_text(pdf_path, pymupdf.Rect(240, 65, 415, 105), page)
    print_rect_text(pdf_path, pymupdf.Rect(245, 40, 425, 90), page)


