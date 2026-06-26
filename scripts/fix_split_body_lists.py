#!/usr/bin/env python3
"""Une viñetas partidas: </ul> + <p class="body"> continuación → mismo <li>."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BOOKS = ("liderar.html", "transformar.html", "bonus.html", "mesa.html")

_SPLIT = re.compile(
    r"<ul class=\"body-list\">(.*?)</ul>\s*<p class=\"body\">(.*?)</p>",
    re.DOTALL,
)
_LI = re.compile(r"<li>(.*?)</li>", re.DOTALL)
_ADJ_UL = re.compile(r"</ul>\s*<ul class=\"body-list\">")


def _needs_merge(li_text: str, cont: str) -> bool:
    t = re.sub(r"\s+", " ", li_text).strip()
    c = re.sub(r"\s+", " ", cont).strip()
    if not t or not c:
        return False
    if t.endswith("—"):
        return True
    if t.endswith((",", " un", " una", " el", " la", " los", " las", " de", " que", " en", " a", " y", " o", " no")):
        return True
    if not t.endswith((".", "!", "?")):
        return True
    # PDF: misma columna sin viñeta nueva — continuación corta del ítem
    if c.startswith("¿") and "¿" in t:
        return True
    if len(c) <= 120 and not re.match(
        r"^(Cuando |Y |Si |Por |En |Al |Para |Después |Antes |Ahora |Este |Esta |Los |Las )",
        c,
    ):
        return True
    return False


def _merge_once(html: str) -> tuple[str, int]:
    n = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal n
        block, cont = m.group(1), m.group(2)
        lis = list(_LI.finditer(block))
        if not lis:
            return m.group(0)
        last = lis[-1]
        li_text = last.group(1)
        if not _needs_merge(li_text, cont):
            return m.group(0)
        merged = f"{li_text.rstrip()} {cont.lstrip()}"
        new_block = block[: last.start(1)] + merged + block[last.end(1) :]
        n += 1
        return f'<ul class="body-list">{new_block}</ul>'

    html = _SPLIT.sub(repl, html)
    return html, n


def fix_html(html: str) -> tuple[str, int]:
    total = 0
    while True:
        html, n = _merge_once(html)
        total += n
        if n == 0:
            break
    while True:
        new = _ADJ_UL.sub("", html)
        if new == html:
            break
        html = new
        total += 1
    return html, total


def main(argv: list[str]) -> int:
    paths = [WEB / a for a in argv[1:]] if len(argv) > 1 else [WEB / b for b in BOOKS]
    for path in paths:
        if not path.is_file():
            print(f"skip {path}")
            continue
        html, n = fix_html(path.read_text(encoding="utf-8"))
        if n:
            path.write_text(html, encoding="utf-8")
        print(f"{'OK' if n else '—'} {path.name}: {n} arreglo(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
