#!/usr/bin/env python3
"""Quita slot de foto (placeholder) — sin imagen, fondo limpio."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"

PAGE_BG = (0.8745, 0.8784, 0.8588)
SAGE_SLOT = (0.7843, 0.8039, 0.7882)


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
            return fitz.Rect(r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 2)
    return None


def remove_photo_slot(page: fitz.Page) -> bool:
    slot = photo_slot_rect(page)
    if slot is None:
        return False
    page.add_redact_annot(slot, fill=PAGE_BG)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: remove_photo_slot.py <página> [página...]", file=sys.stderr)
        return 1

    pages = [int(p) for p in sys.argv[1:]]
    doc = fitz.open(PDF)
    done = []
    for p in pages:
        if 1 <= p <= doc.page_count and remove_photo_slot(doc[p - 1]):
            done.append(p)

    if not done:
        print("No se encontró slot de foto", file=sys.stderr)
        doc.close()
        return 1

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → sin foto en páginas {done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
