#!/usr/bin/env python3
"""Compara HTML generado vs PDF fuente — detecta truncados y palabras pegadas."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_liderar_html import (  # noqa: E402
    extract_lines as extract_liderar,
    is_mov_cover as is_mov_liderar,
    is_tag_line as tag_liderar,
    mov_tag_text as mov_tag_liderar,
)
from build_transformar_html import (  # noqa: E402
    extract_lines as extract_transformar,
    is_mov_cover as is_mov_transformar,
    is_tag_line as tag_transformar,
    mov_tag_text as mov_tag_transformar,
)
from html_blocks import join_prose_lines, mov_cover_subtitle_lines  # noqa: E402
from pdf_text import _label_words, _raw_has_merged_words  # noqa: E402

BOOKS = (
    (
        "transformar",
        ROOT / "El_arte_de_transformar_tu_hogar_v11.pdf",
        ROOT / "web" / "transformar.html",
        extract_transformar,
        is_mov_transformar,
        mov_tag_transformar,
        tag_transformar,
    ),
    (
        "liderar",
        ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf",
        ROOT / "web" / "liderar.html",
        extract_liderar,
        is_mov_liderar,
        mov_tag_liderar,
        tag_liderar,
    ),
)

# Palabras pegadas típicas del bug letter-spacing (DISEÑADORADEL, LIMPIEZAPROFUNDA…)
_GLUE_IN_WORD = re.compile(
    r"(?:"
    r"[A-ZÁÉÍÓÚÑ]{15,}|"
    r"[A-ZÁÉÍÓÚÑ]+DEL[A-ZÁÉÍÓÚÑ]+|"
    r"LA[A-ZÁÉÍÓÚÑ]{6,}|"
    r"[A-ZÁÉÍÓÚÑ]{8,}PROFUNDA|"
    r"LARENUNCIA|LAAUSENCIA|LAFILOSOFÍA|LAARMONÍA"
    r")"
)


def _pdf_mov_subs(doc, extract_fn, is_mov_fn, mov_tag_fn, tag_fn) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for pi in range(len(doc)):
        lines = extract_fn(doc[pi])
        if is_mov_fn(lines):
            subs = mov_cover_subtitle_lines(lines, tag_fn)
            out.append((mov_tag_fn(lines), join_prose_lines(subs)))
    return out


def _html_mov_subs(html: str) -> list[str]:
    return re.findall(
        r'movimiento-cover">.*?<p class="subtitle">([^<]*)</p>', html, re.S
    )


def _html_glued_numbered(html: str) -> list[str]:
    bad: list[str] = []
    for m in re.finditer(r'numbered-title">([^<]+)<', html):
        title = m.group(1).strip()
        for w in _label_words(title):
            if _GLUE_IN_WORD.fullmatch(w):
                bad.append(title)
                break
    return bad


def audit_book(
    name,
    pdf_path,
    html_path,
    extract_fn,
    is_mov_fn,
    mov_tag_fn,
    tag_fn,
) -> list[str]:
    issues: list[str] = []
    if not pdf_path.is_file():
        return [f"{name}: falta PDF {pdf_path.name}"]
    if not html_path.is_file():
        return [f"{name}: falta HTML {html_path.name}"]

    doc = fitz.open(pdf_path)
    html = html_path.read_text(encoding="utf-8")

    pdf_subs = _pdf_mov_subs(doc, extract_fn, is_mov_fn, mov_tag_fn, tag_fn)
    html_subs = _html_mov_subs(html)
    if len(pdf_subs) != len(html_subs):
        issues.append(
            f"{name}: portadas movimiento html={len(html_subs)} pdf={len(pdf_subs)}"
        )
    for (tag, pdf_sub), html_sub in zip(pdf_subs, html_subs):
        if pdf_sub and html_sub != pdf_sub:
            issues.append(f"{name} {tag}: subtítulo html={html_sub!r} pdf={pdf_sub!r}")
        elif pdf_sub and not html_sub:
            issues.append(f"{name} {tag}: subtítulo vacío en HTML pdf={pdf_sub!r}")

    for title in _html_glued_numbered(html):
        issues.append(f"{name}: título pegado {title!r}")

    if re.search(r'pull-page-quote">\s*</', html):
        issues.append(f"{name}: cita pull-page vacía")

    return issues


def main() -> int:
    all_issues: list[str] = []
    for args in BOOKS:
        all_issues.extend(audit_book(*args))

    if all_issues:
        print("AUDIT FAIL")
        for i in all_issues:
            print(" -", i)
        return 1

    print("AUDIT OK — transformar + liderar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
