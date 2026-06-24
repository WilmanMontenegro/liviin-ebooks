#!/usr/bin/env python3
"""Quita slot de foto y sube el contenido — espacio vacío abajo."""

from __future__ import annotations

import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"

PAGE_BG = (0.8745, 0.8784, 0.8588)
WHITE_BG = (1.0, 1.0, 1.0)
SAGE_SLOT = (0.7843, 0.8039, 0.7882)
TARGET_TOP = 58.0
CONTENT_MIN_Y = 295.0  # bajo placeholder FOTO EDITORIAL (~254pt)


def parse_args() -> tuple[Path, list[int]]:
    pages: list[int] = []
    pdf = DEFAULT_PDF
    for arg in sys.argv[1:]:
        p = Path(arg)
        if arg.endswith(".pdf"):
            pdf = p if p.is_absolute() else ROOT / p
        else:
            pages.append(int(arg))
    return pdf, pages


def page_bg(pdf: Path) -> tuple[float, float, float]:
    name = pdf.name.lower()
    if "bonus" in name or "manos" in name or "transformar" in name:
        return WHITE_BG
    return PAGE_BG


def footer_y(page: fitz.Page) -> float:
    return page.rect.height - 42.0


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


def content_lines(page: fitz.Page, footer: float) -> tuple[list[dict], float]:
    """Extrae spans de contenido (sin pie)."""
    spans: list[dict] = []
    min_y = 9999.0
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            y0 = line["bbox"][1]
            if y0 >= footer:
                continue
            if y0 < CONTENT_MIN_Y:
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
    return spans, min_y


def reflow_page(page: fitz.Page, bg: tuple[float, float, float]) -> bool:
    footer = footer_y(page)
    slot = photo_slot_rect(page)
    spans, first_y = content_lines(page, footer)
    if not spans or first_y > 900:
        # Sin slot sage: usar hueco superior (foto ya borrada)
        first_y = min(s["y"] for s in spans) if spans else 0
        if first_y < CONTENT_MIN_Y:
            return False
        shift = first_y - TARGET_TOP
    else:
        shift = first_y - TARGET_TOP

    if shift < 20:
        return False

    # Limpiar zona contenido (no pie)
    page.add_redact_annot(fitz.Rect(0, 45, page.rect.width, footer), fill=bg)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)

    for s in spans:
        page.insert_text(
            (s["x"], s["y"] - shift),
            s["text"],
            fontname=s["font"],
            fontsize=s["size"],
            color=s["color"],
        )

    return True


def main() -> int:
    pdf, pages = parse_args()
    if not pages:
        print("Uso: remove_photo_slot.py <página> [página...] [archivo.pdf]", file=sys.stderr)
        return 1
    if not pdf.exists():
        print(f"No existe PDF: {pdf}", file=sys.stderr)
        return 1

    bg = page_bg(pdf)
    doc = fitz.open(pdf)
    done = []
    for p in pages:
        if 1 <= p <= doc.page_count and reflow_page(doc[p - 1], bg):
            done.append(p)

    if not done:
        print("No se pudo reacomodar", file=sys.stderr)
        doc.close()
        return 1

    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp.replace(pdf)
    print(f"OK → {pdf.name} páginas {done}: sin foto, texto arriba")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
