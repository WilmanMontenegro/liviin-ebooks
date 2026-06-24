#!/usr/bin/env python3
"""Detecta .page con scrollHeight > 864px — en PDF viejo se cortaba .banda."""
from __future__ import annotations

import http.server
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PAGE_MIN_H = 864

BOOKS = ("transformar.html", "liderar.html", "bonus.html")


def _free_port() -> int:
    import socket as s

    with s.socket(s.AF_INET, s.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def audit_html(base: str, name: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    issues: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 576, "height": 864})
        page.goto(f"{base}/{name}", wait_until="networkidle", timeout=120_000)
        page.evaluate("() => document.fonts.ready")
        rows = page.evaluate(
            f"""() => Array.from(document.querySelectorAll('.page')).map((el, i) => ({{
              i: i + 1,
              h: el.scrollHeight,
              folio: el.querySelector('.banda .banda-texto:last-child')?.textContent?.trim() || ''
            }})).filter(x => x.h > {PAGE_MIN_H})"""
        )
        for r in rows:
            issues.append(
                f"{name} p{r['i']} folio={r['folio']!r}: {r['h']}px > {PAGE_MIN_H}px (banda cortada en PDF fijo)"
            )
        browser.close()
    return issues


def main() -> int:
    port = _free_port()
    threading.Thread(
        target=lambda: http.server.HTTPServer(
            ("127.0.0.1", port),
            lambda *a, **k: http.server.SimpleHTTPRequestHandler(
                *a, directory=str(WEB), **k
            ),
        ).serve_forever(),
        daemon=True,
    ).start()
    time.sleep(0.2)
    base = f"http://127.0.0.1:{port}"

    all_issues: list[str] = []
    for name in BOOKS:
        path = WEB / name
        if path.is_file():
            all_issues.extend(audit_html(base, name))

    if all_issues:
        print("OVERFLOW (info — export per-page ya no corta banda):")
        for i in all_issues:
            print(" -", i)
        return 0

    print("OVERFLOW OK — ninguna .page supera 864px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
