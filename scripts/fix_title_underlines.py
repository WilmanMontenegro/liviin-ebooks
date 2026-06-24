#!/usr/bin/env python3
"""Quita rayita larga arriba (artefacto) y restaura la corta bajo el título."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"

PAGE_BG = (0.8745, 0.8784, 0.8588)
UNDERLINE = (0.7098, 0.6588, 0.5686)
UNDERLINE_X = (46.5, 91.5)
GAP_BELOW_TITLE = 7.5
LINE_H = 0.75

REFLOWED = [13, 17, 26, 34, 39, 44, 51, 60]


def title_bottom(page: fitz.Page) -> float | None:
    best = None
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            bb = line["bbox"]
            if bb[1] > 200:
                continue
            if max(s["size"] for s in line["spans"]) < 14:
                continue
            if best is None or bb[3] > best:
                best = bb[3]
    return best


def clear_stray_lines(page: fitz.Page) -> None:
    """Borra rayitas en zona superior (artefactos del reflow)."""
    for d in page.get_drawings():
        r = d.get("rect")
        if not r or r.height > 3:
            continue
        if r.y0 < 140 and (r.width > 80 or r.x0 < 100):
            page.add_redact_annot(
                fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1), fill=PAGE_BG
            )
    page.apply_redactions()


def fix_page(page: fitz.Page) -> bool:
    bottom = title_bottom(page)
    if bottom is None:
        return False
    clear_stray_lines(page)
    y = bottom + GAP_BELOW_TITLE
    # Limpia franja bajo título por si quedaron capas duplicadas
    page.add_redact_annot(
        fitz.Rect(40, y - 3, 100, y + LINE_H + 3), fill=PAGE_BG
    )
    page.apply_redactions()
    page.draw_rect(
        fitz.Rect(UNDERLINE_X[0], y, UNDERLINE_X[1], y + LINE_H),
        color=UNDERLINE,
        fill=UNDERLINE,
        overlay=True,
    )
    return True


def main() -> int:
    pages = [int(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else REFLOWED
    doc = fitz.open(PDF)
    done = []
    for p in pages:
        if 1 <= p <= doc.page_count and fix_page(doc[p - 1]):
            done.append(p)
    if not done:
        print("Nada que corregir", file=sys.stderr)
        doc.close()
        return 1
    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → rayita bajo título en páginas {done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
