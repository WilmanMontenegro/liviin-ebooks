#!/usr/bin/env python3
"""Chequeo de salud: ¿el PDF abre, 92 páginas, sin corrupción obvia?"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz
import pikepdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
EXPECTED_PAGES = 92


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    ok = True

    try:
        with pikepdf.open(path) as pdf:
            n = len(pdf.pages)
            print(f"pikepdf: OK — {n} páginas")
            if path == PDF and n != EXPECTED_PAGES:
                print(f"  ⚠ esperadas {EXPECTED_PAGES}")
                ok = False
    except Exception as e:
        print(f"pikepdf: ROTO — {e}")
        ok = False

    try:
        doc = fitz.open(path)
        print(f"pymupdf: OK — {doc.page_count} páginas, {path.stat().st_size} bytes")
        for i in range(min(3, doc.page_count)):
            _ = doc[i].get_text()[:50]
        doc.close()
    except Exception as e:
        print(f"pymupdf: ROTO — {e}")
        ok = False

    if not ok:
        print("\n→ Restaurar: ./scripts/restore_backup.sh")
        print("→ Portada pro: .venv/bin/python insert_cover.py")
        return 1
    print("PDF sano.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
