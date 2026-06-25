#!/usr/bin/env python3
"""Audita el PDF: páginas, placeholders, imágenes, texto sospechoso."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
from paths import LIDERAR_PDF, LIDERAR_BACKUP

PDF = LIDERAR_PDF
BACKUP = LIDERAR_BACKUP

PLACEHOLDER_RE = re.compile(
    r"FOTO\s*PORTADA|Foto\s+editorial|◇|PLACEHOLDER|\[imagen\]",
    re.IGNORECASE,
)


def audit(path: Path) -> dict:
    doc = fitz.open(path)
    rows = []
    for i, page in enumerate(doc):
        text = page.get_text()
        words = page.get_text("words")
        hits = PLACEHOLDER_RE.findall(text)
        imgs = page.get_images()
        rows.append(
            {
                "page": i + 1,
                "images": len(imgs),
                "words": len(words),
                "placeholders": hits,
                "empty": len(text.strip()) < 5,
            }
        )
    doc.close()
    return {"path": str(path), "pages": len(rows), "rows": rows}


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PDF
    if not target.exists():
        print(f"No existe: {target}", file=sys.stderr)
        return 1

    r = audit(target)
    ph_pages = [x for x in r["rows"] if x["placeholders"]]
    empty = [x for x in r["rows"] if x["empty"]]
    no_img = [x for x in r["rows"] if x["images"] == 0 and x["page"] == 1]

    print(f"Archivo: {r['path']}")
    print(f"Páginas: {r['pages']}")
    print(f"Placeholders: {len(ph_pages)} páginas")
    for x in ph_pages[:20]:
        print(f"  p.{x['page']:>3}: {x['placeholders']}")
    if len(ph_pages) > 20:
        print(f"  ... +{len(ph_pages) - 20} más")
    print(f"Páginas casi vacías: {len(empty)}")
    if target == PDF and BACKUP.exists():
        b = audit(BACKUP)
        print(f"\nBackup: {b['pages']} págs, placeholders {sum(1 for x in b['rows'] if x['placeholders'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
