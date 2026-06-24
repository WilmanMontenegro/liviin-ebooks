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
PHOTO = ROOT / "2023-09-11 17.36.28.jpg"
PAGE_INDEX = 89  # página 90

# Caja interior (foto); marco punteado exterior se elimina al insertar
PHOTO_RECT = fitz.Rect(48.0, 202.0, 120.0, 274.0)
FRAME_OUTER = fitz.Rect(46.5, 200.25, 121.5, 275.25)
PAGE_BG = (0.8745, 0.8784, 0.8588)
SAGE = (0.7843, 0.8039, 0.7882)
PLACEHOLDER_WORDS = {"F", "O", "T", "M", "E", "◇"}


def prepare_photo(path: Path, size_px: int = 600) -> bytes:
    img = Image.open(path).convert("RGB")
    side = min(img.width, img.height)
    left = (img.width - side) // 2
    # Retrato: cuadrado superior (rostro visible en caja pequeña)
    top = 0 if img.height > img.width else (img.height - side) // 2
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


def replace_photo(page: fitz.Page, jpeg: bytes) -> None:
    # Marco punteado + fondo sage del slot → fondo de página; luego solo la foto
    page.add_redact_annot(FRAME_OUTER, fill=PAGE_BG)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
    page.insert_image(PHOTO_RECT, stream=jpeg, keep_proportion=True, overlay=True)


def main() -> int:
    photo = Path(sys.argv[1]) if len(sys.argv) > 1 else PHOTO
    if not photo.exists():
        print(f"No existe foto: {photo}", file=sys.stderr)
        return 1
    if not PDF.exists():
        print(f"No existe PDF: {PDF}", file=sys.stderr)
        return 1

    jpeg = prepare_photo(photo)
    doc = fitz.open(PDF)
    page = doc[PAGE_INDEX]
    replace_photo(page, jpeg)

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → p.90 foto {photo.name} en {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
