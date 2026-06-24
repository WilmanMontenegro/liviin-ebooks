#!/usr/bin/env python3
"""Corrige números del índice (p.10) para que coincidan con el PDF."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
INDEX_PAGE = 9  # página 10

# Pie de página = número PDF donde empieza cada movimiento.
INDEX_PAGES = {
    "04": "05",  # De mí para ti
    "12": "11",  # Movimiento 01 (apertura)
    "24": "24",  # Movimiento 02 — ya correcto
    "36": "37",  # Movimiento 03
    "56": "58",  # Movimiento 04
    "68": "74",  # Bonus
    "84": "87",  # Cierre
}

PAGE_BG = (0.8745, 0.8784, 0.8588)
NUM_COLOR = (153 / 255, 143 / 255, 138 / 255)  # #998F8A
FONT = "helv"
FONT_SIZE = 9.0
NUM_RIGHT_X = 384.3


def fix_index(page: fitz.Page) -> int:
    changed = 0
    # Solo números alineados a la derecha del índice (x > 370).
    targets = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if x0 > 370 and word in INDEX_PAGES:
            targets.append((fitz.Rect(x0, y0, x1, y1), word, INDEX_PAGES[word]))

    for rect, old, new in targets:
        if old == new:
            continue
        page.add_redact_annot(rect, fill=PAGE_BG)
        changed += 1

    if changed:
        page.apply_redactions()

    for rect, old, new in targets:
        if old == new:
            continue
        width = fitz.get_text_length(new, fontname=FONT, fontsize=FONT_SIZE)
        x = NUM_RIGHT_X - width
        y = rect.y1 - 2.5  # baseline
        page.insert_text((x, y), new, fontname=FONT, fontsize=FONT_SIZE, color=NUM_COLOR)

    return changed


def main() -> int:
    if not PDF.exists():
        print(f"No existe: {PDF}", file=sys.stderr)
        return 1

    doc = fitz.open(PDF)
    n = fix_index(doc[INDEX_PAGE])
    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → índice actualizado ({n} números) en {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
