#!/usr/bin/env -S uv run

import argparse
import re
from pathlib import Path

import sys
import pymupdf
import time

from utils.ocr_utils import extract_text_or_ocr, create_ocr, ocr_rotated_rect


DEFAULT_REGEX_FLAGS = re.IGNORECASE | re.DOTALL


def spaced_letters(text):
    return r"\s*".join(map(re.escape, text))


MARKER_ZONES = {
    "portrait": (130, 0, 480, 110),
    "landscape": (250, 0, 450, 75),
}


DOCUMENTS = [
    {
        "name": "AVL Invoice",
        "orientation": "portrait",
        "marker": r"custom.*?inv..ce",
        "id_regions": [
            ((240, 65, 415, 105), r"invo.ce.*?(\d{10,})"),
            ((245, 40, 425, 90), r"invo.ce.*?(\d{10,})"),
        ],
        "file": "AVL-Invoice-{1}.pdf",
    },
    {
        "name": "AVL Invoice Ref Page",
        "orientation": "portrait",
        "marker": r"reference\s*page",
        "id_regions": [
            ((240, 45, 425, 80), r"invo.ce.*?(\d{8,})"),
        ],
        "file": "AVL-Invoice-{1}.pdf",
    },
    {
        "name": "SLI",
        "orientation": "portrait",
        "marker": r"h.{0,3}pp.{0,16}ett.{0,16}f.{0,7}ruct",
        "id_regions": [
            ((285, 55, 380, 95), r"(?<!\d)152\d{7}(?!\d)"),
        ],
        "file": "SLI-{0}.pdf",
    },
    {
        "name": "Portrait Packing List",
        "orientation": "portrait",
        "marker": r"packing\s*list",
        "id_regions": [
            ((0, 250, 85, 285), r"(\d{7,})"),
        ],
        "file": "Packing-List-{1}.pdf",
    },
    {
        "name": "Export Summary",
        "orientation": "portrait",
        "marker": spaced_letters("exportsummary"),
        "id_regions": [
            ((65, 185, 165, 230), r"(\d{7,})"),
        ],
        "file": "Packing-List-{1}.pdf",
    },
    {
        "name": "AWB",
        "orientation": "portrait",
        "marker": r"air\s*waybill",
        "file": "AWB.pdf",
    },
    {
        "name": "SWB",
        "orientation": "portrait",
        "marker": r"international\s+ocean",
        "file": "SWB.pdf",
    },
    {
        "name": "Landscape Packing List",
        "orientation": "landscape",
        "marker": r"packing\s*list",
        "id_regions": [
            ((0, 50, 255, 85), r"delivery.*?(\d{7,})"),
        ],
        "file": "Packing-List-{1}.pdf",
    },
    {
        "name": "APL Invoice",
        "orientation": "landscape",
        "marker": r"invoice.*?(\d{10,})",
        "file": "APL-Invoice-{1}.pdf",
    },
]

CONTINUATIONS = [
    {
        "name": "SLI Ref Page",
        "orientation": "portrait",
        "marker": r"reference\s*page",
        "previous_file": r"^SLI-.*\.pdf$",
    },
]


FALLBACKS = [
    {
        "name": "Misoriented Landscape Packing List",
        "orientation": "portrait",
        "id_regions": [
            ((30, 500, 100, 792), r"delivery.*?(\d{7,})"),
        ],
        "file": "Packing-List-{1}.pdf",
    },
    {
        "name": "Misoriented Portrait Invoice",
        "orientation": "portrait",
        "marker": r"invoice.*?(\d{10,})",
        "id_regions": [
            ((20, 350, 80, 650), r"invoice.*?(\d{10,})"),
        ],
        "file": "APL-Invoice-{1}.pdf",
    },
]


def get_marker_text(page, ocr, orientation):
    coords = MARKER_ZONES[orientation]
    return extract_text_or_ocr(page, pymupdf.Rect(*coords), ocr)


def search_region(page, region, ocr):
    coords, pattern = region
    text = extract_text_or_ocr(page, pymupdf.Rect(*coords), ocr)
    return re.search(pattern, text, DEFAULT_REGEX_FLAGS)


def make_filename(file_rule, match=None):
    if match is None:
        return file_rule

    values = [match.group(0), *match.groups()]
    return file_rule.format(*values)


def match_document(page, doc, ocr, orientation, marker_text_value):
    expected_orientation = doc.get("orientation")

    if expected_orientation and orientation != expected_orientation:
        return None

    marker_match = re.search(doc["marker"], marker_text_value, DEFAULT_REGEX_FLAGS)

    if not marker_match:
        return None

    id_regions = doc.get("id_regions", [])

    if not id_regions:
        return make_filename(doc["file"], marker_match)

    for id_region in id_regions:
        if id_match := search_region(page, id_region, ocr):
            return make_filename(doc["file"], id_match)

    return None


def get_orientation(page):
    return "landscape" if page.rect.width > page.rect.height else "portrait"


def detect_document(page, ocr):
    orientation = get_orientation(page)
    marker_text = get_marker_text(page, ocr, orientation)

    for doc in DOCUMENTS:
        if file_name := match_document(page, doc, ocr, orientation, marker_text):
            return file_name, orientation, marker_text

    return None, orientation, marker_text


def matches_continuation(rule, previous_file_name, orientation, marker_text):
    return (
        previous_file_name
        and (not rule.get("orientation") or orientation == rule["orientation"])
        and re.search(rule["previous_file"], previous_file_name, DEFAULT_REGEX_FLAGS)
        and re.search(rule["marker"], marker_text, DEFAULT_REGEX_FLAGS)
    )


def get_continuation_file(previous_file_name, orientation, marker_text):
    for rule in CONTINUATIONS:
        if matches_continuation(rule, previous_file_name, orientation, marker_text):
            return previous_file_name

    return None


def search_rotated_region(page, region, ocr, dpi=150, rotate=-90):
    coords, pattern = region

    text = ocr_rotated_rect(
        page,
        pymupdf.Rect(*coords),
        ocr,
        dpi=dpi,
        rotate=rotate,
    )

    #print("fallback OCR:", repr(text))

    return re.search(pattern, text, DEFAULT_REGEX_FLAGS)

def get_fallback_file(page, ocr, orientation):
    for rule in FALLBACKS:
        if rule.get("orientation") and orientation != rule["orientation"]:
            continue

        for id_region in rule.get("id_regions", []):
            if id_match := search_rotated_region(
                page,
                id_region,
                ocr,
            ):
                return make_filename(rule["file"], id_match)
    return None

def group_pages(input_pdf, ocr):
    groups = {}
    previous_file_name = None

    with pymupdf.open(input_pdf) as doc:
        for page_index, page in enumerate(doc):
            file_name, orientation, marker_text = detect_document(page, ocr)

            file_name = (
                file_name
                or get_continuation_file(previous_file_name, orientation, marker_text)
                or get_fallback_file(page, ocr, orientation)
                or "other.pdf"
            )

            groups.setdefault(file_name, []).append(page_index)

            previous_file_name = None if file_name == "other.pdf" else file_name

    return groups


def write_groups(input_pdf, groups):
    output_dir = Path.cwd() / "outputs" / f"{input_pdf.stem}_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(input_pdf) as src:
        for file_name, page_indexes in groups.items():
            with pymupdf.open() as output:
                for page_index in page_indexes:
                    output.insert_pdf(
                        src,
                        from_page=page_index,
                        to_page=page_index,
                    )

                output.save(output_dir / file_name)


def process_pdf(input_pdf, ocr):
    groups = group_pages(input_pdf, ocr)

    for file_name, pages in groups.items():
        print(f"{file_name}: {[p + 1 for p in pages]}")

    write_groups(input_pdf, groups)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", help="PDF to split")
    args = parser.parse_args()
    input_pdf = Path(args.input_pdf)

    ocr = create_ocr()

    if len(sys.argv) < 2:
        sys.exit(1)

    folder_path = sys.argv[1]
    input_pdf = Path(folder_path)

    if not input_pdf.exists():
        sys.exit(1)

    if input_pdf.is_dir():
        pdf_files = sorted(input_pdf.rglob("*.pdf"))

        if not pdf_files:
           sys.exit(1)

        for pdf in pdf_files:
           print(f"\n Processing {pdf}")
           process_pdf(pdf, ocr)

    else: 
        process_pdf(input_pdf, ocr)


if __name__ == "__main__":
    start = time.perf_counter()

    main()

    end = time.perf_counter()
    print(f"\n Execution Time: {end - start:.2f} seconds")