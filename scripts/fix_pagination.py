#!/usr/bin/env python3
"""Pie derecho: número de página del libro (1–92) en lugar de 00/01/… repetidos."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
from paths import LIDERAR_PDF

PDF = LIDERAR_PDF

FOOTER_TEXT_COLOR = (250 / 255, 240 / 255, 240 / 255)  # #FAF0F0
FOOTER_BAR = (0.671, 0.620, 0.584)
FONT = "helv"
FONT_SIZE = 7.5
NUM_RIGHT_X = 386.0
NUM_BASELINE_Y = 630.5


def has_footer_bar(page: fitz.Page) -> bool:
    for d in page.get_drawings():
        r = d.get("rect")
        if r and r.y0 >= 607 and r.height >= 35 and r.width >= 400:
            return True
    return False


def footer_right_words(page: fitz.Page) -> list[tuple]:
    return [w for w in page.get_text("words") if w[1] > 608 and w[0] > 355]


def should_redact(word: str) -> bool:
    return bool(re.fullmatch(r"\d", word) or word in {"B", "✦", "◆", "★"})


def insert_page_num(page: fitz.Page, page_num: int) -> None:
    text = str(page_num)
    width = fitz.get_text_length(text, fontname=FONT, fontsize=FONT_SIZE)
    x = NUM_RIGHT_X - width
    page.insert_text(
        (x, NUM_BASELINE_Y),
        text,
        fontname=FONT,
        fontsize=FONT_SIZE,
        color=FOOTER_TEXT_COLOR,
    )


def fix_page(page: fitz.Page, page_num: int) -> bool:
    if not has_footer_bar(page):
        return False

    redacted = False
    for x0, y0, x1, y1, word, *_ in footer_right_words(page):
        if should_redact(word):
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=FOOTER_BAR)
            redacted = True

    if redacted:
        page.apply_redactions()

    insert_page_num(page, page_num)
    return True


def main() -> int:
    if not PDF.exists():
        print(f"No existe: {PDF}", file=sys.stderr)
        return 1

    doc = fitz.open(PDF)
    changed = 0
    for i, page in enumerate(doc):
        if fix_page(page, i + 1):
            changed += 1

    tmp = PDF.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(PDF)
    print(f"OK → {changed} páginas con número de libro en {PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
