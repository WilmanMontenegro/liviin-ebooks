#!/usr/bin/env python3
"""Quita slot de foto y sube el contenido — espacio vacío abajo."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"

PAGE_BG = (0.8745, 0.8784, 0.8588)
SAGE_SLOT = (0.7843, 0.8039, 0.7882)
LINE_COLOR = (0.710, 0.659, 0.569)
TARGET_TOP = 58.0
FOOTER_Y = 600.0


def rgb(c: int) -> tuple[float, float, float]:
    return ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255


def map_font(name: str, flags: int) -> str:
    italic = "Italic" in name or (flags & 2)
    bold = bool(flags & 16) or (flags & 4 and "Serif" in name)
    if "Serif" in name or name == "Times-Roman":
        if bold and italic:
            return "tibi"
        if bold:
            return "tibo"
        if italic:
            return "tiro"
        return "times"
    if bold:
        return "hebo"
    return "helv"


def photo_slot_rect(page: fitz.Page) -> fitz.Rect | None:
    for d in page.get_drawings():
        r = d.get("rect")
        fill = d.get("fill")
        if not r or not fill:
            continue
        if (
            r.width > 300
            and 200 < r.height < 280
            and 40 < r.x0 < 60
            and abs(fill[0] - SAGE_SLOT[0]) < 0.02
        ):
            return fitz.Rect(r)
    return None


def content_lines(page: fitz.Page) -> tuple[list[dict], list[fitz.Rect], float]:
    """Extrae spans de contenido (sin pie) y líneas decorativas."""
    spans: list[dict] = []
    min_y = 9999.0
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            y0 = line["bbox"][1]
            if y0 >= FOOTER_Y:
                continue
            if y0 < 250:  # ya sin placeholder
                continue
            min_y = min(min_y, y0)
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                ox, oy = s["origin"]
                spans.append(
                    {
                        "text": s["text"],
                        "x": ox,
                        "y": oy,
                        "font": map_font(s["font"], s["flags"]),
                        "size": s["size"],
                        "color": rgb(s["color"]),
                    }
                )

    hlines: list[fitz.Rect] = []
    for d in page.get_drawings():
        r = d.get("rect")
        if not r or r.height > 2 or r.width < 20:
            continue
        if 250 < r.y0 < FOOTER_Y and r.x0 < 100:
            hlines.append(fitz.Rect(r))

    return spans, hlines, min_y


def reflow_page(page: fitz.Page) -> bool:
    slot = photo_slot_rect(page)
    spans, hlines, first_y = content_lines(page)
    if not spans or first_y > 900:
        # Sin slot sage: usar hueco superior (foto ya borrada)
        first_y = min(s["y"] for s in spans) if spans else 0
        if first_y < 250:
            return False
        shift = first_y - TARGET_TOP
    else:
        shift = first_y - TARGET_TOP

    if shift < 20:
        return False

    # Limpiar zona contenido (no pie)
    page.add_redact_annot(fitz.Rect(0, 45, page.rect.width, FOOTER_Y), fill=PAGE_BG)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

    for s in spans:
        page.insert_text(
            (s["x"], s["y"] - shift),
            s["text"],
            fontname=s["font"],
            fontsize=s["size"],
            color=s["color"],
        )

    for r in hlines:
        nr = fitz.Rect(r.x0, r.y0 - shift, r.x1, r.y1 - shift)
        page.draw_rect(nr, color=LINE_COLOR, fill=LINE_COLOR, overlay=True)

    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: remove_photo_slot.py <página> [página...]", file=sys.stderr)
        return 1

    pages = [int(p) for p in sys.argv[1:]]
    doc = fitz.open(PDF)
    done = []
    for p in pages:
        if 1 <= p <= doc.page_count and reflow_page(doc[p - 1]):
            done.append(p)

    if not done:
        print("No se pudo reacomodar", file=sys.stderr)
        doc.close()
        return 1

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → contenido subido, sin foto en páginas {done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
