#!/usr/bin/env python3
"""Extrae texto por página de un PDF → JSON (borrador para web)."""
import argparse
import json
import sys
from pathlib import Path

import fitz


def extract(pdf_path: Path, start: int, end: int) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(start - 1, min(end, doc.page_count)):
        pages.append({"page": i + 1, "text": doc[i].get_text()})
    doc.close()
    return pages


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pdf", type=Path)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--from", dest="start", type=int, default=1)
    p.add_argument("--to", dest="end", type=int, default=10)
    args = p.parse_args()
    data = extract(args.pdf, args.start, args.end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(data)} páginas → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
