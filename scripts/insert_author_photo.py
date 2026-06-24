#!/usr/bin/env python3
"""Foto autora en página 90 (placeholder FOTO MTE)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
PHOTO = ROOT / "ebook 1.png"
PAGE_INDEX = 89  # página 90

# Caja interior del marco punteado
PHOTO_RECT = fitz.Rect(48.0, 202.0, 120.0, 274.0)
SAGE = (0.7843, 0.8039, 0.7882)
PLACEHOLDER_WORDS = {"F", "O", "T", "M", "E", "◇"}


def prepare_photo(path: Path, size_px: int = 600) -> bytes:
    img = Image.open(path).convert("RGB")
    side = min(img.size)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    sq = img.crop((left, top, left + side, top + side))
    sq = sq.resize((size_px, size_px), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    sq.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


def redact_placeholder(page: fitz.Page) -> None:
    # Solo letras del bloque FOTO MTE + diamante, dentro de la caja
    box = fitz.Rect(46, 198, 123, 278)
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if word in PLACEHOLDER_WORDS and fitz.Rect(x0, y0, x1, y1).intersects(box):
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=SAGE)
    page.apply_redactions()


def insert_photo(page: fitz.Page, jpeg: bytes) -> None:
    page.draw_rect(PHOTO_RECT, color=SAGE, fill=SAGE, overlay=False)
    page.insert_image(PHOTO_RECT, stream=jpeg, keep_proportion=True, overlay=True)


def main() -> int:
    if not PHOTO.exists():
        print(f"No existe foto: {PHOTO}", file=sys.stderr)
        return 1
    if not PDF.exists():
        print(f"No existe PDF: {PDF}", file=sys.stderr)
        return 1

    jpeg = prepare_photo(PHOTO)
    doc = fitz.open(PDF)
    page = doc[PAGE_INDEX]
    redact_placeholder(page)
    insert_photo(page, jpeg)

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → p.90 foto insertada en {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
