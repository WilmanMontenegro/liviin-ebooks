#!/usr/bin/env python3
"""Fase 1: Mesa → cascarón ebook.css (como Liderar). Textos intactos."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESA = ROOT / "web" / "mesa.html"

CREDITS_OLD = """<div class="page">
  <div class="page-content">
    <div style="height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 0 0.5in;">

      <div class="etiqueta" style="margin-bottom: 24pt;">LIVIIN · LANZAMIENTO 2</div>

      <h2 class="display-lg" style="margin-bottom: 14pt;">El arte de liderar tu mesa</h2>

      <p class="lead" style="margin-bottom: 20pt; max-width: 4in;">Bonus exclusivo del Lanzamiento 2 — Liviin</p>

      <div class="filete-center" style="margin: 16pt auto;"></div>

      <p style="font-size: 9pt; max-width: 4in; color: var(--texto-2); margin-bottom: 12pt;">Todos los derechos reservados. Esta guía está pensada para acompañar a la dueña del hogar en la planeación y dirección de la alimentación familiar.</p>

      <p style="font-size: 9pt; max-width: 4in; color: var(--texto-2); margin-bottom: 28pt;">Su contenido no sustituye la asesoría profesional en nutrición, salud o seguridad alimentaria. Consulta a un especialista para necesidades médicas o dietéticas específicas.</p>

      <div class="filete-center" style="margin: 16pt auto;"></div>

      <p class="muted" style="font-size: 8.5pt; letter-spacing: 0.1em; margin-top: 8pt;">© LIVIIN · FOR BETTER LIVING</p>
      <p class="muted" style="font-size: 8.5pt; font-style: italic;">Primera edición digital · 2026</p>

    </div>
  </div>
</div>"""

CREDITS_NEW = """<div class="page">
  <div class="content" style="display:flex;flex-direction:column;justify-content:center;">
    <div class="spacer-xl"></div>
    <span class="tag">LIVIIN · LANZAMIENTO 2</span>
    <div class="h1" style="font-size:36px;margin-bottom:6px;">El arte de<br>liderar tu mesa</div>
    <div class="rule"></div>
    <div class="spacer-lg"></div>
    <p class="body" style="font-size:10px;color:var(--secundario);font-style:italic;">Bonus exclusivo del Lanzamiento 2 — Liviin</p>
    <div class="spacer-md"></div>
    <p class="body" style="font-size:10px;color:var(--secundario);">Todos los derechos reservados. Esta guía está pensada para acompañar a la dueña del hogar en la planeación y dirección de la alimentación familiar.</p>
    <p class="body" style="font-size:10px;color:var(--secundario);">Su contenido no sustituye la asesoría profesional en nutrición, salud o seguridad alimentaria. Consulta a un especialista para necesidades médicas o dietéticas específicas.</p>
    <div class="spacer-lg"></div>
    <p style="font-family:var(--sans);font-size:8.5px;letter-spacing:0.1em;color:var(--filete);text-transform:uppercase;">© LIVIIN · FOR BETTER LIVING</p>
    <p style="font-family:var(--serif-text);font-size:11px;font-style:italic;color:var(--filete);margin-top:4px;">Primera edición digital · 2026</p>
  </div>
  <div class="banda"><span class="banda-texto">LIVIIN · LANZAMIENTO 2</span><span class="banda-texto"></span></div>
</div>"""


def _convert_portadilla(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        label = m.group(1).strip()
        title = m.group(2).replace("<br/>", "<br>")
        ancla = m.group(3)
        return (
            f'<div class="page">\n'
            f'  <div class="content movimiento-cover">\n'
            f'    <span class="tag">{label}</span>\n'
            f'    <div class="h1">{title}</div>\n'
            f'    <div class="rule"></div>\n'
            f'    <div class="spacer-sm"></div>\n'
            f'    <p class="subtitle">{ancla}</p>\n'
            f'  </div>\n'
            f'</div>'
        )

    pat = re.compile(
        r'<div class="page">\s*<div class="portadilla">\s*'
        r'<div class="portadilla-numero">—\s*(.+?)\s*—</div>\s*'
        r'<h1 class="portadilla-titulo">(.*?)</h1>\s*'
        r'<p class="portadilla-ancla">(.*?)</p>\s*'
        r'</div>\s*</div>',
        re.S,
    )
    return pat.sub(repl, html)


def _convert_respiracion(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        quote = m.group(1).replace("<br/>", "<br>")
        return (
            f'<div class="page page-crema">\n'
            f'  <div class="content cierre-final">\n'
            f'    <div class="pull-page">\n'
            f'      <div class="pull-page-quote">{quote}</div>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'</div>'
        )

    pat = re.compile(
        r'<div class="page respiracion-page">\s*<div class="respiracion">\s*'
        r'<p class="respiracion-texto">(.*?)</p>\s*'
        r'<div class="respiracion-filete"></div>\s*'
        r'</div>\s*</div>',
        re.S,
    )
    return pat.sub(repl, html)


def _convert_banda(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        mov = m.group(1).strip().upper()
        num = m.group(2).lstrip("0") or "0"
        return (
            f'  <div class="banda">'
            f'<span class="banda-texto">{mov}</span>'
            f'<span class="banda-texto">{num}</span></div>'
        )

    pat = re.compile(
        r'\s*<div class="banda-inferior">\s*'
        r'<span class="banda-movimiento">(.*?)</span>\s*'
        r'<span class="banda-numero">(\d+)</span>\s*'
        r'</div>',
        re.S,
    )
    return pat.sub(repl, html)


def _wrap_pull_quotes(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        if inner.startswith("<p"):
            return m.group(0)
        return f'<div class="pull-quote"><p>{inner}</p></div>'

    return re.sub(
        r'<div class="pull-quote">(.*?)</div>',
        repl,
        html,
        flags=re.S,
    )


def main() -> None:
    html = MESA.read_text(encoding="utf-8")
    html = html.replace('href="css/liviin.css"', 'href="css/ebook.css"')
    html = html.replace(CREDITS_OLD, CREDITS_NEW)
    html = html.replace('page-content with-band', "content")
    html = html.replace('class="page-content"', 'class="content"')
    html = html.replace('class="etiqueta"', 'class="tag"')
    html = html.replace('class="titulo-pagina"', 'class="h2"')
    html = html.replace('<div class="filete"></div>', '<div class="rule"></div>')
    html = html.replace('class="lead"', 'class="body"')
    html = _convert_portadilla(html)
    html = _convert_respiracion(html)
    html = _convert_banda(html)
    html = _wrap_pull_quotes(html)
    MESA.write_text(html, encoding="utf-8")
    print("OK", MESA)
    print("  banda:", html.count('class="banda"'))
    print("  liviin.css:", "liviin.css" in html)
    print("  page-content:", "page-content" in html)
    print("  banda-inferior:", "banda-inferior" in html)


if __name__ == "__main__":
    main()
