#!/usr/bin/env python3
"""Audita énfasis editorial PDF Liderar vs HTML (barrita / cursiva / pull-page)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_liderar_html import extract_lines, is_margin_noise  # noqa: E402
from html_blocks import group_has_pull_vline, pull_vlines_from_page  # noqa: E402

PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
HTML = ROOT / "web" / "liderar.html"


def _pdf_vline_quotes() -> list[tuple[int, str]]:
    doc = fitz.open(PDF)
    found: list[tuple[int, str]] = []
    for pi in range(len(doc)):
        page = doc[pi]
        lines = extract_lines(page)
        page_h = max((ln.y for ln in lines), default=0) + 25
        lines = [ln for ln in lines if not is_margin_noise(ln, page_h, pi + 1)]
        vl = pull_vlines_from_page(page)
        if not vl:
            continue
        i = 0
        while i < len(lines):
            ln = lines[i]
            if not ln.italic or ln.size > 14:
                i += 1
                continue
            g = [ln]
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if not nxt.italic or nxt.size > 14:
                    break
                if abs(nxt.x - ln.x) > 4 or nxt.y - g[-1].y > 22:
                    break
                g.append(nxt)
                j += 1
            if group_has_pull_vline(g, vl):
                text = re.sub(r"\s+", " ", " ".join(x.text.strip() for x in g)).strip()
                if pi + 1 > 2:  # skip portada
                    found.append((pi + 1, text))
            i = j if j > i else i + 1
    doc.close()
    return found


def _html_pull_quotes() -> list[str]:
    html = HTML.read_text(encoding="utf-8")
    return [re.sub(r"\s+", " ", t).strip() for t in re.findall(r'pull-quote"><p>([^<]+)</p>', html)]


def _match(pdf_text: str, html_texts: list[str]) -> bool:
    p = pdf_text[:50]
    return any(p in h or pdf_text in h for h in html_texts)


def main() -> int:
    if not PDF.is_file() or not HTML.is_file():
        print("Falta PDF o liderar.html")
        return 1

    pdf_q = _pdf_vline_quotes()
    html_q = _html_pull_quotes()
    missing = [(p, t) for p, t in pdf_q if not _match(t, html_q)]

    print("DISEÑO PDF → HTML (Liderar)")
    print(f"  Citas con barrita en PDF (contenido): {len(pdf_q)}")
    print(f"  pull-quote en HTML: {len(html_q)}")
    print(f"  body--italic en HTML: {HTML.read_text().count('body body--italic')}")
    print(f"  pull-page (hoja sola): {HTML.read_text().count('pull-page-quote')}")

    if missing:
        print("\nFALTAN en HTML (barrita PDF):")
        for p, t in missing:
            print(f"  p{p}: {t[:75]!r}")
        return 1

    print("\nOK — citas con barrita alineadas al PDF editorial")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
