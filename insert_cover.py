#!/usr/bin/env python3
"""Portada editorial: reemplaza foto superior de pág. 1."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
COVER_IMAGE = ROOT / "portada ebook 1.png"

# Donde empieza "LIVIIN · EBOOK 01" (fijo en el PDF).
TEXT_START_Y = 391.0
# Fin de la foto: deja respiro sage antes del texto.
COVER_GAP_PT = 30.0
COVER_BOTTOM_Y = TEXT_START_Y - COVER_GAP_PT
SAGE = (200, 205, 201)
SAGE_PDF = tuple(c / 255 for c in SAGE)


def cover_rect(page: fitz.Page) -> fitz.Rect:
    return fitz.Rect(0, 0, page.rect.width, COVER_BOTTOM_Y)


def prepare_cover(path: Path, width: int, height: int) -> bytes:
    image = Image.open(path).convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize(
        (int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS
    )
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    cropped = resized.crop((left, top, left + width, top + height))

    fade_h = min(110, height // 4)
    pixels = cropped.load()
    for row in range(height - fade_h, height):
        t = (row - (height - fade_h)) / fade_h
        for col in range(width):
            r, g, b = pixels[col, row]
            pixels[col, row] = (
                int(r * (1 - t) + SAGE[0] * t),
                int(g * (1 - t) + SAGE[1] * t),
                int(b * (1 - t) + SAGE[2] * t),
            )

    out = io.BytesIO()
    cropped.save(out, format="JPEG", quality=92, optimize=True, progressive=True)
    return out.getvalue()


def replace_cover(page: fitz.Page, jpeg: bytes) -> None:
    img_rect = cover_rect(page)
    clear_rect = fitz.Rect(0, 0, page.rect.width, TEXT_START_Y)
    page.add_redact_annot(clear_rect, fill=SAGE_PDF)
    page.apply_redactions()
    page.insert_image(img_rect, stream=jpeg, keep_proportion=False, overlay=True)


def main() -> int:
    cover = Path(sys.argv[1]) if len(sys.argv) > 1 else COVER_IMAGE
    if not cover.exists():
        print(f"No existe foto: {cover}", file=sys.stderr)
        return 1
    if not PDF.exists():
        print(f"No existe PDF: {PDF}", file=sys.stderr)
        return 1

    doc = fitz.open(PDF)
    page = doc[0]
    rect = cover_rect(page)
    px_w = max(1, int(rect.width / 72 * 200))
    px_h = max(1, int(rect.height / 72 * 200))

    jpeg = prepare_cover(cover, px_w, px_h)
    replace_cover(page, jpeg)

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → portada {cover.name} en {PDF} ({px_w}x{px_h}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
