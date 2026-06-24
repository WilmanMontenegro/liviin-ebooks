#!/usr/bin/env python3
"""Actualiza la fecha de web/index.html al publicar."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def stamp_text(when: datetime | None = None) -> str:
    dt = when or datetime.now(ZoneInfo("America/Bogota"))
    return f"{dt.day} de {MESES[dt.month - 1]} de {dt.year}, {dt.hour:02d}:{dt.minute:02d}"


def main() -> None:
    label = stamp_text()
    text = INDEX.read_text(encoding="utf-8")
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
