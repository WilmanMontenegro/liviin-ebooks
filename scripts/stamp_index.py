#!/usr/bin/env python3
"""Actualiza fecha y metadatos de tarjetas en web/index.html."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = WEB / "index.html"
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# slug → título h2 en index.html
BOOKS: tuple[tuple[str, str], ...] = (
    ("liderar.html", "El arte de liderar tu hogar"),
    ("transformar.html", "El arte de transformar tu hogar"),
    ("bonus.html", "Las manos que sostienen tu hogar"),
)


def stamp_text(when: datetime | None = None) -> str:
    dt = when or datetime.now(ZoneInfo("America/Bogota"))
    return f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}, {dt.hour:02d}:{dt.minute:02d}"


def page_count(html_path: Path) -> int:
    text = html_path.read_text(encoding="utf-8")
    return len(re.findall(r'<div class="page', text))


def card_meta(slug: str, pages: int) -> str:
    """Misma estructura en las tres tarjetas: páginas + tipo."""
    if slug == "bonus.html":
        return f"{pages} páginas · bonus de cortesía · portada editorial."
    return f"{pages} páginas · portada editorial."


def stamp_cards(text: str) -> str:
    for slug, title in BOOKS:
        pages = page_count(WEB / slug)
        blurb = card_meta(slug, pages)
        pattern = (
            rf'(<h2>{re.escape(title)}</h2>\s*<p>)[^<]+(</p>)'
        )
        text, n = re.subn(pattern, rf"\g<1>{blurb}\g<2>", text, count=1)
        if not n:
            raise SystemExit(f"no encontré tarjeta para {title!r}")
    return text


def main() -> None:
    label = stamp_text()
    text = INDEX.read_text(encoding="utf-8")
    text = stamp_cards(text)
    new, n = re.subn(
        r"(Actualizado:\s*)[^.<]+(\.)",
        rf"\g<1>{label}\2",
        text,
        count=1,
    )
    if not n:
        raise SystemExit("no encontré línea Actualizado: en web/index.html")
    INDEX.write_text(new, encoding="utf-8")
    print(f"OK index → {label}")


if __name__ == "__main__":
    main()
