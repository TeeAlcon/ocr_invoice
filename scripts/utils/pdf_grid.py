#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pillow>=12.2.0",
#     "pymupdf>=1.27.2.3",
# ]
#
# [tool.uv]
# exclude-newer = "7 days"
# ///

from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw
import argparse

def render_page_with_grid(pdf_path, page_num=1, dpi=150, step_pt=50, out_path=None):
    """
    Render PDF page with a coordinate grid in PDF points.
    Useful for visually choosing PyMuPDF Rect coordinates.
    """
    pdf_path = Path(pdf_path)
    out_path = out_path or pdf_path.with_name(f"{pdf_path.stem}_p{page_num}_grid.png")

    zoom = dpi / 72

    with pymupdf.open(pdf_path) as doc:
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        pix.save(out_path)

        img = Image.open(out_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        width_pt = page.rect.width
        height_pt = page.rect.height

        # Grid lines every step_pt PDF points
        for x_pt in range(0, int(width_pt) + 1, step_pt):
            x_px = int(x_pt * zoom)
            draw.line([(x_px, 0), (x_px, img.height)], fill=(255, 0, 0), width=1)
            draw.text((x_px + 3, 3), str(x_pt), fill=(255, 0, 0))

        for y_pt in range(0, int(height_pt) + 1, step_pt):
            y_px = int(y_pt * zoom)
            draw.line([(0, y_px), (img.width, y_px)], fill=(0, 0, 255), width=1)
            draw.text((3, y_px + 3), str(y_pt), fill=(0, 0, 255))

        img.save(out_path)

    print(f"Wrote: {out_path}")
    return out_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Render a PDF page with a coordinate grid.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("-p", "--page", type=int, default=1, help="Page number, 1-based")
    parser.add_argument("--dpi", type=int, default=150, help="Render DPI")
    parser.add_argument("--step", type=int, default=50, help="Grid spacing in PDF points")
    parser.add_argument("-o", "--out", default=None, help="Output PNG path")

    args = parser.parse_args()

    render_page_with_grid(
        args.pdf,
        page_num=args.page,
        dpi=args.dpi,
        step_pt=args.step,
        out_path=args.out,
    )

if __name__ == "__main__":
    main()

