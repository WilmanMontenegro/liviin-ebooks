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

# ponytail: mismo trim que .page en tokens.css (576×864); scale 2 = nitidez al zoom sin vector print
PAGE_W_PX = 576
PX_TO_PT = 72 / 96
EXPORT_SCALE = 2

BOOKS: dict[str, tuple[str, str]] = {
    "liderar": ("liderar.html", "liderar.pdf"),
    "transformar": ("transformar.html", "transformar.pdf"),
    "bonus": ("bonus.html", "bonus.pdf"),
    "mesa": ("mesa.html", "mesa.pdf"),
    "imprimible": ("imprimible.html", "imprimible.pdf"),
}

# ponytail: imprimible = solo hojas .print-page (sin .page editorial ni imágenes)
PAGE_SELECTOR: dict[str, str] = {
    "imprimible.html": ".print-page",
}

# Captura pantalla por .page — print PDF partía páginas altas y cortaba .banda.
EXPORT_SCREEN_CSS = """
body.pdf-export { background: #fff !important; margin: 0 !important; }
body.pdf-export .page,
body.pdf-export .print-page {
  margin: 0 !important;
  box-shadow: none !important;
}
body.pdf-export .hub-link { display: none !important; }
"""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _serve_web(port: int) -> None:
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(WEB), **k
    )
    http.server.HTTPServer(("127.0.0.1", port), handler).serve_forever()


def _selector(html_name: str) -> str:
    return PAGE_SELECTOR.get(html_name, ".page")


def _set_visible_page(page, selector: str, index: int) -> None:
    page.evaluate(
        """({ sel, i }) => {
          document.querySelectorAll(sel).forEach((el, j) => {
            el.style.display = j === i ? 'flex' : 'none';
          });
        }""",
        {"sel": selector, "i": index},
    )


def export_one(base_url: str, html_name: str, out_path: Path) -> None:
    import fitz
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": PAGE_W_PX, "height": 1200},
            device_scale_factor=EXPORT_SCALE,
        )
        page = context.new_page()
        page.goto(f"{base_url}/{html_name}", wait_until="networkidle", timeout=120_000)
        page.evaluate("() => document.fonts.ready")
        page.evaluate("() => document.body.classList.add('pdf-export')")
        page.add_style_tag(content=EXPORT_SCREEN_CSS)

        sel = _selector(html_name)
        n = page.locator(sel).count()
        if not n:
            context.close()
            browser.close()
            raise RuntimeError(f"Sin hojas ({sel}) en {html_name}")

        merged = fitz.open()
        for i in range(n):
            _set_visible_page(page, sel, i)
            loc = page.locator(sel).nth(i)
            box = loc.bounding_box()
            if not box:
                continue
            img = loc.screenshot(type="png")
            w_pt = box["width"] * PX_TO_PT
            h_pt = box["height"] * PX_TO_PT
            sheet = fitz.open()
            pg = sheet.new_page(width=w_pt, height=h_pt)
            pg.insert_image(fitz.Rect(0, 0, w_pt, h_pt), stream=img)
            merged.insert_pdf(sheet)
            sheet.close()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        merged.save(str(out_path), garbage=4, deflate=True)
        merged.close()
        context.close()
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
        help="liderar | transformar | bonus | mesa | imprimible | all",
    )
    args = ap.parse_args()
    keys = list(BOOKS.keys()) if not args.books or args.books == ["all"] else args.books
    export_books(keys)


if __name__ == "__main__":
    main()
