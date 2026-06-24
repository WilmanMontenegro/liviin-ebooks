#!/usr/bin/env python3
"""Portada editorial: reemplaza foto superior de pág. 1."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
DEFAULT_COVER = ROOT / "portada ebook 1.png"

COVER_GAP_PT = 10.0
SAGE = (200, 205, 201)  # fade libro liderar
WHITE = (255, 255, 255)  # fade libro transformar (hoja blanca)
HEAD_TRIM_OF_EXCESS = 0.12


def detect_text_start_y(page: fitz.Page) -> float:
    rows: dict[float, list[str]] = {}
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        rows.setdefault(round(y0, 1), []).append(word)
    for y in sorted(rows):
        words = rows[y]
        joined = "".join(words)
        if "LIVIIN" in joined and "·" in joined:
            return y
        if "·" in words and "0" in words and "2" in words:
            return y
        joined = "".join(words)
        if "EBOOK" in joined:
            return y
    return 391.0  # ponytail: fallback libro liderar


def page_fade_rgb(pdf: Path) -> tuple[int, int, int]:
    name = pdf.name.lower()
    if "transformar" in name or "manos" in name or "bonus" in name:
        return WHITE
    return SAGE


def prepare_cover(
    path: Path, width: int, height: int, fade_rgb: tuple[int, int, int]
) -> bytes:
    image = Image.open(path).convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize(
        (int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS
    )
    left = max(0, (resized.width - width) // 2)
    if image.height > image.width:
        excess = max(0, resized.height - height)
        top = int(excess * HEAD_TRIM_OF_EXCESS)
    else:
        top = (resized.height - height) // 2
    cropped = resized.crop((left, top, left + width, top + height))

    fade_h = min(110, height // 4)
    fade_start = height - fade_h
    pixels = cropped.load()
    for row in range(fade_start, height):
        t = (row - fade_start) / fade_h
        for col in range(width):
            r, g, b = pixels[col, row]
            pixels[col, row] = (
                int(r * (1 - t) + fade_rgb[0] * t),
                int(g * (1 - t) + fade_rgb[1] * t),
                int(b * (1 - t) + fade_rgb[2] * t),
            )

    out = io.BytesIO()
    cropped.save(out, format="JPEG", quality=92, optimize=True, progressive=True)
    return out.getvalue()


def replace_cover(
    page: fitz.Page, jpeg: bytes, bottom_pt: float, fade_rgb: tuple[int, int, int]
) -> None:
    img_rect = fitz.Rect(0, 0, page.rect.width, bottom_pt)
    fill = tuple(c / 255 for c in fade_rgb)
    page.add_redact_annot(img_rect, fill=fill)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
    page.insert_image(img_rect, stream=jpeg, keep_proportion=False, overlay=True)


def main() -> int:
    cover = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COVER
    pdf = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PDF
    if not cover.exists():
        print(f"No existe foto: {cover}", file=sys.stderr)
        return 1
    if not pdf.exists():
        print(f"No existe PDF: {pdf}", file=sys.stderr)
        return 1

    doc = fitz.open(pdf)
    page = doc[0]
    text_start_y = detect_text_start_y(page)
    fade_rgb = page_fade_rgb(pdf)
    bottom_pt = text_start_y - COVER_GAP_PT

    px_w = max(1, int(page.rect.width / 72 * 200))
    px_h = max(1, int(bottom_pt / 72 * 200))

    jpeg = prepare_cover(cover, px_w, px_h, fade_rgb)
    replace_cover(page, jpeg, bottom_pt, fade_rgb)

    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(pdf)
    print(
        f"OK → portada {cover.name} en {pdf.name} "
        f"(fade={fade_rgb}, gap={COVER_GAP_PT:.0f}pt, y={text_start_y:.0f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
