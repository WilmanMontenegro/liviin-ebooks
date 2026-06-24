#!/usr/bin/env python3
"""Exporta ebooks HTML (web/) → PDF para descarga — WYSIWYG del piloto web."""
from __future__ import annotations

import argparse
import http.server
import socket
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT_DIR = WEB / "pdf"

# ponytail: mismo trim que .page en tokens.css (576×864)
PAGE_W_PX = 576
PAGE_H_PX = 864

BOOKS: dict[str, str] = {
    "liderar": ("liderar.html", "liderar.pdf"),
    "transformar": ("transformar.html", "transformar.pdf"),
    "bonus": ("bonus.html", "bonus.pdf"),
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _serve_web(port: int) -> None:
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(WEB), **k
    )
    http.server.HTTPServer(("127.0.0.1", port), handler).serve_forever()


def export_one(base_url: str, html_name: str, out_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": PAGE_W_PX, "height": PAGE_H_PX})
        page.goto(f"{base_url}/{html_name}", wait_until="networkidle", timeout=120_000)
        page.evaluate("() => document.fonts.ready")
        page.emulate_media(media="print")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        page.pdf(
            path=str(out_path),
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()


def export_books(names: list[str]) -> None:
    port = _free_port()
    threading.Thread(target=_serve_web, args=(port,), daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    for key in names:
        html_name, pdf_name = BOOKS[key]
        out = OUT_DIR / pdf_name
        export_one(base, html_name, out)
        pages = 0
        try:
            import fitz

            pages = len(fitz.open(out))
        except Exception:
            pass
        print(f"OK {out}" + (f" — {pages} páginas" if pages else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description="HTML ebook → PDF (web/pdf/)")
    ap.add_argument(
        "books",
        nargs="*",
        choices=[*BOOKS.keys(), "all"],
        default=["all"],
        help="liderar | transformar | bonus | all",
    )
    args = ap.parse_args()
    keys = list(BOOKS.keys()) if not args.books or args.books == ["all"] else args.books
    export_books(keys)


if __name__ == "__main__":
    main()
