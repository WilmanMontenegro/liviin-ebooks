#!/usr/bin/env python3
"""Inserta QR en página 89 (placeholder [Código QR aquí])."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
QR_SRC = ROOT / "HOME EXCEL CODIGO QR.png"
PAGE_INDEX = 88  # página 89

# Caja blanca interior; marco punteado exterior se elimina al insertar
QR_RECT = fitz.Rect(276.0, 293.0, 355.5, 372.5)
FRAME_OUTER = fitz.Rect(274.5, 291.0, 357.0, 373.5)
WHITE = (1.0, 1.0, 1.0)


def prepare_qr(path: Path, size_px: int = 512) -> bytes:
    img = Image.open(path).convert("RGB")
    # Solo módulos oscuros del QR (sin esquinas verdes ni marco gris del screenshot)
    mask = Image.new("L", img.size)
    px = img.load()
    mp = mask.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = px[x, y]
            mp[x, y] = 255 if r < 140 and g < 140 and b < 140 else 0
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError(f"QR vacío: {path}")
    cropped = img.crop(bbox)
    side = max(cropped.size)
    sq = Image.new("RGB", (side, side), "white")
    ox = (side - cropped.width) // 2
    oy = (side - cropped.height) // 2
    sq.paste(cropped, (ox, oy))
    sq = sq.resize((size_px, size_px), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    sq.save(out, format="PNG", optimize=True)
    return out.getvalue()


def redact_placeholder(page: fitz.Page) -> None:
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if word in ("[Código", "QR", "aquí]"):
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=WHITE)
    page.apply_redactions()


def replace_qr(page: fitz.Page, png: bytes) -> None:
    page.add_redact_annot(FRAME_OUTER, fill=WHITE)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
    page.insert_image(QR_RECT, stream=png, keep_proportion=True, overlay=True)


def main() -> int:
    if not QR_SRC.exists():
        print(f"No existe QR: {QR_SRC}", file=sys.stderr)
        return 1
    if not PDF.exists():
        print(f"No existe PDF: {PDF}", file=sys.stderr)
        return 1

    png = prepare_qr(QR_SRC)
    doc = fitz.open(PDF)
    page = doc[PAGE_INDEX]
    redact_placeholder(page)
    replace_qr(page, png)

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → p.89 QR insertado en {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
