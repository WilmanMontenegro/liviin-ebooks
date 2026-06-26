#!/usr/bin/env python3
"""Quita estilos inline repetidos de web/mesa.html → clases en ebook.css."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESA = ROOT / "web" / "mesa.html"

# ponytail: mapa literal estilo→clase; orden importa (más específico primero)
STYLE_TO_CLASS: tuple[tuple[str, str], ...] = (
    ('<ol class="numbered" style="columns: 2; column-gap: 14pt; font-size: 9pt; line-height: 1.4;">',
     '<ol class="numbered numbered--2col numbered--dense">'),
    ('<ol class="numbered" style="columns: 2; column-gap: 18pt; margin-top: 6pt;">',
     '<ol class="numbered numbered--2col numbered--2col-wide">'),
    ('<ol class="numbered" style="columns: 2; column-gap: 14pt; margin-top: 8pt;">',
     '<ol class="numbered numbered--2col">'),
    ('<ol class="numbered" style="columns: 2; column-gap: 14pt;">',
     '<ol class="numbered numbered--2col">'),
    ('<ol class="numbered-circles" style="margin-top: 10pt;">',
     '<ol class="numbered-circles numbered-circles--spaced">'),
    ('<div class="filete-full" style="margin: 2pt 0 4pt;"></div>',
     '<div class="filete-full filete-full--tight"></div>'),
    ('<div class="filete-full" style="margin: 1pt 0 3pt;"></div>',
     '<div class="filete-full filete-full--flush"></div>'),
    ('<div class="filete" style="margin: 6pt 0;"></div>', '<div class="filete filete--tight"></div>'),
    ('<div class="filete" style="margin: 5pt 0;"></div>', '<div class="filete filete--snug"></div>'),
    ('<h3 class="display-sm" style="margin-top: 2pt; margin-bottom: 2pt;">',
     '<h3 class="display-sm display-sm--tight">'),
    ('<h3 class="display-sm" style="margin-top: 8pt; margin-bottom: 2pt;">',
     '<h3 class="display-sm display-sm--after-gap">'),
    ('<p class="muted" style="margin-top: 14pt;">', '<p class="muted muted--spaced">'),
    ('<p style="font-size: 8.5pt; line-height: 1.55;">', '<p class="lista-mercado">'),
    ('<p style="font-size: 9.5pt;">', '<p class="lead-bank">'),
    (' style="margin-top: 10pt; text-align: center;"', ' class="text-center-block"'),
    (' style="text-align:center;max-width:320px;margin:24px auto;"', ' class="text-center-narrow"'),
    (' style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 14pt;"', ' class="bank-grid"'),
    (' style="margin:12px 0;"', ' class="spacer-inline"'),  # fallback abajo
    ('<ol class="numbered" style="font-size: 8pt; line-height: 1.35;">', '<ol class="numbered numbered--xs">'),
    ('<ol class="numbered" style="font-size: 9pt; line-height: 1.4;">', '<ol class="numbered numbered--sm">'),
    (' start="1" style="font-size: 9pt; line-height: 1.4;"', ' start="1" class="numbered--sm"'),
    (' start="3" style="font-size: 9pt; line-height: 1.4;"', ' start="3" class="numbered--sm"'),
    (' start="4" style="font-size: 9pt; line-height: 1.4;"', ' start="4" class="numbered--sm"'),
    (' start="8" style="font-size: 9pt; line-height: 1.4;"', ' start="8" class="numbered--sm"'),
    ('<ol class="numbered" style="columns: 2; column-gap: 18pt; margin-top: 4pt;">',
     '<ol class="numbered numbered--2col numbered--2col-wide numbered--2col-start">'),
    ('<h3 class="display-sm" style="margin-top: 0; margin-bottom: 1pt;">', '<h3 class="display-sm display-sm--flush">'),
    ('<h3 class="display-sm" style="margin-top: 6pt; margin-bottom: 1pt;">', '<h3 class="display-sm display-sm--sub">'),
    ('<h3 class="display-sm" style="margin-top: 4pt; margin-bottom: 1pt; font-size: 10pt;">',
     '<h3 class="display-sm display-sm--minor">'),
    ('<h3 class="display-sm" style="margin-top: 4pt; margin-bottom: 2pt;">', '<h3 class="display-sm display-sm--tight">'),
    ('<ul style="font-size: 9pt; line-height: 1.5;">', '<ul class="list-compact">'),
    ('<div class="pull-quote" style="margin-top: 18pt;">', '<div class="pull-quote pull-quote--spaced">'),
    ('<p style="margin-top: 12pt; font-family: \'Cormorant Garamond\', serif; font-style: italic; color: var(--olivo); font-size: 12pt;">',
     '<p class="kicker-serif kicker-serif--closing">'),
    ('<p style="margin-top: 14pt; font-family: \'Cormorant Garamond\', serif; font-style: italic; color: var(--texto-2); font-size: 10pt; text-align: center;">',
     '<p class="quote-center">'),
    ('<p style="font-family: \'Inter\', sans-serif; font-size: 8pt; color: #665E53; font-style: italic; margin-top: 10pt; line-height: 1.4;">',
     '<p class="bank-note">'),
    ('<strong style="color: #4A5C4E;">', '<strong>'),
    (' style="margin-top: 10pt;"', ''),
    (' style="margin-top: 8pt;"', ''),
    (' style="margin-top: 6pt;"', ''),
    (' style="margin-top: 4pt;"', ''),
    (' style="margin-top: 14pt;"', ''),
    (' style="margin-top: 18pt; font-family: \'Cormorant Garamond\', serif; font-style: italic; color: var(--olivo); font-size: 12pt;">',
     ' class="kicker-serif">'),
)

LEGAL_BLOCK_OLD = """  <div class="content" style="display:flex;flex-direction:column;justify-content:center;">
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
    <p style="font-family:var(--serif-text);font-size:11px;font-style:italic;color:var(--filete);margin-top:4px;">Primera edición digital · 2026</p>"""

LEGAL_BLOCK_NEW = """  <div class="content content--legal">
    <div class="spacer-xl"></div>
    <span class="tag">LIVIIN · LANZAMIENTO 2</span>
    <div class="h1 h1--legal">El arte de<br>liderar tu mesa</div>
    <div class="rule"></div>
    <div class="spacer-lg"></div>
    <p class="legal-kicker">Bonus exclusivo del Lanzamiento 2 — Liviin</p>
    <div class="spacer-md"></div>
    <p class="legal-note">Todos los derechos reservados. Esta guía está pensada para acompañar a la dueña del hogar en la planeación y dirección de la alimentación familiar.</p>
    <p class="legal-note">Su contenido no sustituye la asesoría profesional en nutrición, salud o seguridad alimentaria. Consulta a un especialista para necesidades médicas o dietéticas específicas.</p>
    <div class="spacer-lg"></div>
    <p class="legal-mark">© LIVIIN · FOR BETTER LIVING</p>
    <p class="legal-edition">Primera edición digital · 2026</p>"""


def main() -> None:
    text = MESA.read_text(encoding="utf-8")
    if LEGAL_BLOCK_OLD in text:
        text = text.replace(LEGAL_BLOCK_OLD, LEGAL_BLOCK_NEW)

    CLOSING_OLD = """    <p class="body body--italic" class="text-center-narrow">El arte de liderar tu mesa es un bonus del Lanzamiento 2 de Liviin. Forma parte del universo editorial sobre el liderazgo del hogar.</p>
    <div class="rule"></div>
    <p class="body" style="font-family:var(--sans);font-size:9px;letter-spacing:0.16em;color:var(--secundario);text-transform:uppercase;margin-top:24px;margin-bottom:6px;">María Teresa Espinosa</p>
    <p class="body body--italic">Interiorista y Home Coach · MTE</p>
    <p class="body" style="font-family:var(--sans);font-size:9px;letter-spacing:0.16em;color:var(--secundario);text-transform:uppercase;margin-top:20px;">@mte_disenointerior</p>
    <p class="body" style="font-family:var(--sans);font-size:9px;letter-spacing:0.16em;color:var(--secundario);text-transform:uppercase;">@liviinhome</p>
    <p class="body" style="font-family:var(--serif-text);font-size:11px;font-style:italic;color:var(--filete);margin-top:24px;">Primera edición digital · 2026</p>"""

    CLOSING_NEW = """    <p class="body body--italic text-center-narrow">El arte de liderar tu mesa es un bonus del Lanzamiento 2 de Liviin. Forma parte del universo editorial sobre el liderazgo del hogar.</p>
    <div class="rule"></div>
    <p class="social-handle social-handle--lead">María Teresa Espinosa</p>
    <p class="body body--italic">Interiorista y Home Coach · MTE</p>
    <p class="social-handle">@mte_disenointerior</p>
    <p class="social-handle">@liviinhome</p>
    <p class="legal-edition legal-edition--spaced">Primera edición digital · 2026</p>"""

    if CLOSING_OLD in text:
        text = text.replace(CLOSING_OLD, CLOSING_NEW)

    for old, new in STYLE_TO_CLASS:
        text = text.replace(old, new)
    # ponytail: margin:12px 0 en <p> sueltos → quitar (body ya tiene ritmo)
    text = re.sub(r'<p style="margin:12px 0;">', "<p>", text)
    text = re.sub(r'<p style="margin: 1pt 0 3pt;">', "<p>", text)
    text = re.sub(r'<p style="margin-top: 6pt; margin-bottom: 1pt;">', "<p>", text)
    text = re.sub(r'<p style="margin-top: 0; margin-bottom: 1pt;">', "<p>", text)
    text = re.sub(r'<p style="margin-top: 4pt; margin-bottom: 2pt;">', "<p>", text)
    text = re.sub(r'<p style="font-size: 8pt; line-height: 1.35;">', '<p class="lista-mercado">', text)
    text = re.sub(r'<p style="font-size: 9pt; line-height: 1.4;">', '<p class="lead-bank">', text)
    text = re.sub(r'<p style="font-size: 9pt; line-height: 1.5;">', '<p class="lead-bank">', text)
    text = re.sub(r'<p style="font-size: 6\.5pt; line-height: 1\.3;">', '<p class="lista-mercado">', text)
    text = re.sub(r'<ol class="numbered" style="columns: 1;">', '<ol class="numbered">', text)
    remaining = len(re.findall(r'\sstyle="', text))
    MESA.write_text(text, encoding="utf-8")
    print(f"OK mesa.html — estilos inline restantes: {remaining}")
    if remaining:
        for m in sorted(set(re.findall(r'style="[^"]*"', text))):
            print(f"  {m}")


if __name__ == "__main__":
    main()
