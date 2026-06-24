#!/usr/bin/env python3
"""PDF Liderar → HTML plantilla Liviin (bonus.html)."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
BONUS = ROOT / "web" / "bonus.html"
OUT = ROOT / "web" / "liderar.html"

MOVIMIENTOS = [
    (11, "01 · LA FILOSOFÍA"),
    (24, "02 · CONOCE TU CASA"),
    (37, "03 · EQUIPO"),
    (58, "04 · ARMONÍA"),
    (67, "05 · CONVERSACIONES"),
    (74, "SCRIPTS"),
    (87, "EPÍLOGO"),
    (88, "BONUS"),
]

SIGUE_TITLES = {
    "02": "Conoce tu casa",
    "03": "Construir el equipo",
    "04": "Sostener la armonía",
    "05": "Conversaciones esenciales",
    "CIERRE": "El hogar como reflejo",
}


@dataclass
class Line:
    text: str
    size: float
    y: float
    bold: bool = False
    italic: bool = False


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def collapse_spaced(s: str) -> str:
    """PDF caps con letter-spacing: 'E L  C A M B I O' → 'EL CAMBIO'; '0 1' → '01'."""
    s = s.strip()
    if re.fullmatch(r"0\s*\d", s):
        return re.sub(r"\s+", "", s)
    if not re.search(r"(?:\S\s){3,}", s):
        return s
    return " ".join(re.sub(r"\s+", "", c) for c in re.split(r"\s{2,}", s) if c.strip())


def parse_numbered_label(label: str) -> tuple[str, str]:
    if "·" in label:
        left, _, right = label.partition("·")
        return collapse_spaced(left), collapse_spaced(right)
    return "", collapse_spaced(label)


def fmt_caps(s: str) -> str:
    return esc(collapse_spaced(s))


def is_numbered_label(s: str) -> bool:
    return bool(re.match(r"^0\s*\d\s*·", s.strip()))


def is_tag_line(s: str, size: float) -> bool:
    if size > 10.5:
        return False
    t = s.strip()
    if is_numbered_label(t) or t.startswith("SIGUE AL"):
        return False
    return bool(re.search(r"(?:[A-ZÁÉÍÓÚ]\s){3,}", t))


def _footer_key(s: str) -> str:
    return re.sub(r"[^\wáéíóúñ]", "", collapse_spaced(s).lower())


def is_margin_noise(ln: Line, page_h: float, page_no: int) -> bool:
    """Número de página y etiqueta de sección del pie PDF — ya van en .banda."""
    t = ln.text.strip()
    if re.fullmatch(r"\d{1,3}", t) and ln.size < 10:
        return True
    if ln.y <= page_h * 0.9:
        return False
    if _footer_key(t) == _footer_key(section_for(page_no)):
        return True
    if is_numbered_label(t) and ln.size <= 8.5:
        return True
    return False


def extract_lines(page: fitz.Page) -> list[Line]:
    out: list[Line] = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            spans = ln["spans"]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            if not text.strip():
                continue
            out.append(
                Line(
                    text=text.strip(),
                    size=max(s["size"] for s in spans),
                    y=min(s["bbox"][1] for s in spans),
                    bold=any(s["flags"] & 16 for s in spans),
                    italic=any(s["flags"] & 2 for s in spans),
                )
            )
    out.sort(key=lambda x: x.y)
    return out


def section_for(page_no: int) -> str:
    if page_no <= 8:
        return "INICIACIÓN"
    if page_no == 9:
        return "ÍNDICE"
    for start, label in reversed(MOVIMIENTOS):
        if page_no >= start:
            return label
    return "INICIACIÓN"


def is_pull_page(lines: list[Line]) -> bool:
    body = [ln for ln in lines if not (ln.text.startswith("—") and ln.size < 11)]
    if len(body) < 4:
        return False
    if body[0].text.startswith('"') and body[0].size >= 22:
        return True
    big = sum(1 for ln in body if ln.size >= 22)
    return big >= max(4, int(len(body) * 0.75))


def mov_tag_text(lines: list[Line]) -> str:
    for ln in lines:
        compact = re.sub(r"\s+", "", ln.text.upper())
        if compact.startswith("MOVIMIENTO"):
            m = re.search(r"0?(\d+)", compact)
            if m:
                return f"MOVIMIENTO {m.group(1).zfill(2)}"
    return ""


def is_mov_cover(lines: list[Line]) -> bool:
    if not mov_tag_text(lines):
        return False
    extras = sum(1 for ln in lines if ln.size >= 10 and not is_tag_line(ln.text, ln.size))
    return extras <= 5


def _render_prose_group(g: list[Line]) -> list[str]:
    if all(12.5 <= x.size <= 14.5 and x.italic for x in g):
        return [f'<div class="pull-quote"><p>{esc(" ".join(x.text for x in g))}</p></div>']
    text = " ".join(x.text for x in g)
    if any(x.bold for x in g) and len(g) == 1:
        return [f'<p class="body"><strong>{esc(text)}</strong></p>']
    if g[0].text.startswith("— MARÍA") or g[0].text.startswith("Interiorista y Home"):
        return ["""<div class="firma">
      <p class="con-carino">— María Teresa Espinosa</p>
      <p class="nombre">Interiorista y Home Coach · MTE</p>
    </div>"""]
    return [f'<p class="body">{esc(text)}</p>']


def _group_prose(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    groups: list[list[Line]] = []
    cur: list[Line] = []
    prev_bottom: float | None = None
    for ln in lines:
        if prev_bottom is not None and ln.y - prev_bottom > 14:
            if cur:
                groups.append(cur)
                cur = []
        cur.append(ln)
        prev_bottom = ln.y + max(ln.size * 0.35, 8)
    if cur:
        groups.append(cur)
    parts: list[str] = []
    for g in groups:
        parts.extend(_render_prose_group(g))
    return parts


def _extract_bullet_items(lines: list[Line], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    cur: list[str] = []
    i = start
    last_y = lines[start].y
    while i < len(lines):
        ln = lines[i]
        if ln.text.strip() == "•":
            if cur:
                items.append(" ".join(cur))
                cur = []
            i += 1
            continue
        if cur and ln.y - last_y > 34:
            break
        cur.append(ln.text)
        last_y = ln.y
        i += 1
    if cur:
        items.append(" ".join(cur))
    return items, i


def group_paragraphs(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    if not any(ln.text.strip() == "•" for ln in lines):
        return _group_prose(lines)
    parts: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].text.strip() == "•":
            items, i = _extract_bullet_items(lines, i)
            if items:
                lis = "".join(f"<li>{esc(t)}</li>" for t in items)
                parts.append(f'<ul class="body-list">{lis}</ul>')
            continue
        j = i
        while j < len(lines) and lines[j].text.strip() != "•":
            j += 1
        parts.extend(_group_prose(lines[i:j]))
        i = j
    return parts


def parse_sigue(text: str) -> tuple[str, str] | None:
    m = re.search(
        r"SIGUE\s+AL\s+MOVIMIENTO\s+(\d{2})\s*→|SIGUE\s+AL\s+CIERRE\s*→",
        text,
        re.I,
    )
    if not m:
        return None
    if "CIERRE" in m.group(0).upper():
        return ("SIGUE AL CIERRE →", SIGUE_TITLES["CIERRE"])
    return (f"SIGUE AL MOVIMIENTO {m.group(1)} →", SIGUE_TITLES.get(m.group(1), ""))


def banda(section: str, num: int | str, show_num: bool = True) -> str:
    right = str(num) if show_num else ""
    return (
        f'  <div class="banda"><span class="banda-texto">{esc(section)}</span>'
        f'<span class="banda-texto">{right}</span></div>\n'
    )


def cover_page() -> str:
    return """<!-- PORTADA -->
<div class="page">
  <div class="foto-portada"><img src="assets/liderar-portada.jpg" alt=""></div>
  <div class="portada-content">
    <span class="portada-colofon">LIVIIN · EBOOK 01</span>
    <div class="portada-titulo">El arte de<br>liderar<br>tu hogar</div>
    <div class="portada-subtitulo">Una guía para dueñas que quieren un equipo armonioso, comunicación clara y una casa que funciona aunque no estés.</div>
    <div class="portada-liviin">
      <span class="marca">liviin</span>
      <span class="tagline">for better living</span>
    </div>
  </div>
</div>
"""


def legal_page() -> str:
    return """<!-- TÍTULO LEGAL -->
<div class="page">
  <div class="content" style="display:flex;flex-direction:column;justify-content:center;">
    <div class="spacer-xl"></div>
    <span class="tag">LIVIIN · EBOOK 01</span>
    <div class="h1" style="font-size:36px;margin-bottom:6px;">El arte de<br>liderar tu hogar</div>
    <div class="rule"></div>
    <p class="subtitle">Una guía para dueñas que quieren un equipo armonioso, comunicación clara y una casa que funciona aunque no estés.</p>
    <div class="spacer-lg"></div>
    <p style="font-family:var(--sans);font-size:9px;letter-spacing:0.16em;color:var(--secundario);text-transform:uppercase;margin-bottom:6px;">UNA GUÍA DE MARÍA TERESA ESPINOSA</p>
    <p style="font-family:var(--serif-text);font-size:12px;font-style:italic;color:var(--secundario);">Interiorista y Home Coach · MTE</p>
    <div class="spacer-lg"></div>
    <p style="font-family:var(--sans);font-size:8.5px;letter-spacing:0.1em;color:var(--filete);text-transform:uppercase;">© LIVIIN · FOR BETTER LIVING</p>
    <p style="font-family:var(--serif-text);font-size:11px;font-style:italic;color:var(--filete);margin-top:4px;">Primera edición digital · 2026</p>
    <div class="spacer-md"></div>
    <p class="body" style="font-size:10px;color:var(--secundario);">Esta obra está pensada para acompañar a la dueña del hogar en su rol de liderazgo doméstico. Su contenido no sustituye la asesoría profesional en relaciones laborales.</p>
  </div>
  <div class="banda"><span class="banda-texto">LIVIIN · EBOOK 01</span><span class="banda-texto"></span></div>
</div>
"""


def dedicatoria_page(lines: list[Line]) -> str:
    paras = [ln.text for ln in lines if "DEDICATORIA" not in ln.text.upper() and not ln.text.startswith("—")]
    inner = "\n    ".join(f"<p>{esc(t)}</p>" for t in paras)
    return f"""<!-- DEDICATORIA -->
<div class="page page-crema">
  <div class="content dedicatoria">
    <span class="dash">— DEDICATORIA —</span>
    {inner}
  </div>
</div>
"""


def pull_page(lines: list[Line], page_no: int) -> str:
    quote_lines = [ln.text for ln in lines if ln.size >= 20 and not ln.text.startswith("—")]
    attr = next((ln.text for ln in lines if ln.text.startswith("—")), "— MTE · LIVIIN")
    quote = esc(" ".join(quote_lines))
    if not quote.startswith('"'):
        quote = f'"{quote}"'
    return f"""<!-- p{page_no} cita -->
<div class="page page-crema">
  <div class="content" style="display:flex;flex-direction:column;justify-content:center;height:100%;">
    <div class="pull-page">
      <div class="pull-page-quote">{quote}</div>
      <span class="pull-page-attr">{fmt_caps(attr)}</span>
    </div>
  </div>
</div>
"""


def index_page_liderar() -> str:
    items = [
        ("00", "Iniciación · De mí para ti"),
        ("01", "La filosofía del hogar bien llevado"),
        ("02", "Conoce tu casa antes de delegarla"),
        ("03", "Construir el equipo"),
        ("04", "Sostener la armonía en el tiempo"),
        ("05", "Bonus · Conversaciones esenciales"),
        ("06", "Cierre · El hogar como reflejo"),
    ]
    items_html = "\n    ".join(
        f'<div class="numbered-block"><div class="numbered-title"><span class="num">{n}</span> {esc(t)}</div></div>'
        for n, t in items
    )
    return f"""<!-- ÍNDICE -->
<div class="page">
  <div class="content">
    <span class="tag">ÍNDICE</span>
    <div class="h2">El recorrido</div>
    <div class="rule"></div>
    <div class="spacer-sm"></div>
    {items_html}
    <div class="spacer-md"></div>
    <p class="body">Lee a tu ritmo. Cada movimiento puede leerse solo.</p>
  </div>
  {banda("ÍNDICE", 9)}
</div>
"""


def index_page(lines: list[Line]) -> str:
    items: list[str] = []
    note: list[str] = []
    for ln in lines:
        t = ln.text.strip()
        m = re.match(r"^(0\s*\d)\s{2,}(.*)$", t)
        if m:
            items.append((collapse_spaced(m.group(1)), m.group(2).strip()))
        elif "ÍNDICE" in t.upper().replace(" ", "") or t == "El recorrido":
            continue
        elif items:
            note.append(t)
    items_html = "\n    ".join(
        f'<div class="numbered-block"><div class="numbered-title"><span class="num">{esc(n)}</span> {esc(t)}</div></div>'
        for n, t in items
    )
    return f"""<!-- ÍNDICE -->
<div class="page">
  <div class="content">
    <span class="tag">ÍNDICE</span>
    <div class="h2">El recorrido</div>
    <div class="rule"></div>
    <div class="spacer-sm"></div>
    {items_html}
    <div class="spacer-md"></div>
    <p class="body">{esc(" ".join(note))}</p>
  </div>
  {banda("ÍNDICE", 9)}
</div>
"""


def mov_cover_page(lines: list[Line], page_no: int) -> str:
    tag = mov_tag_text(lines)
    titles = [ln for ln in lines if ln.size >= 18 and not is_tag_line(ln.text, ln.size)]
    subs = [ln for ln in lines if 10 <= ln.size <= 14 and not is_tag_line(ln.text, ln.size)]
    title_html = "<br>".join(esc(t.text) for t in titles)
    sub = esc(subs[-1].text) if subs else ""
    return f"""<!-- p{page_no} movimiento -->
<div class="page">
  <div class="content movimiento-cover">
    <span class="tag">{esc(tag)}</span>
    <div class="h1">{title_html}</div>
    <div class="rule"></div>
    <div class="spacer-sm"></div>
    <p class="subtitle">{sub}</p>
  </div>
</div>
"""


def content_page(lines: list[Line], page_no: int) -> str:
    page_h = max((ln.y for ln in lines), default=0) + 25
    lines = [ln for ln in lines if not is_margin_noise(ln, page_h, page_no)]
    sec = section_for(page_no)
    full_text = "\n".join(ln.text for ln in lines)
    sigue = parse_sigue(full_text)
    tokens: list[tuple] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.text.startswith("SIGUE AL"):
            break
        if is_tag_line(ln.text, ln.size):
            tokens.append(("tag", collapse_spaced(ln.text)))
            i += 1
            continue
        if is_numbered_label(ln.text):
            label = ln.text
            i += 1
            desc: list[Line] = []
            while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 16 and not lines[i].text.startswith("SIGUE"):
                desc.append(lines[i])
                i += 1
            tokens.append(("numbered", label, desc))
            continue
        if ln.size >= 16 and not is_tag_line(ln.text, ln.size):
            titles = [ln]
            i += 1
            while i < len(lines) and lines[i].size >= 16 and not is_tag_line(lines[i].text, lines[i].size):
                titles.append(lines[i])
                i += 1
            tokens.append(("title", titles))
            continue
        if ln.text.startswith("—") and ln.size < 12:
            i += 1
            continue
        chunk = [ln]
        i += 1
        while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 16 and not lines[i].text.startswith("SIGUE") and not (lines[i].text.startswith("—") and lines[i].size < 12):
            chunk.append(lines[i])
            i += 1
        tokens.append(("body", chunk))

    parts: list[str] = []
    for tok in tokens:
        if tok[0] == "tag":
            parts.append(f'<span class="tag">{esc(tok[1])}</span>')
            if "CIERRE DEL MOVIMIENTO" in tok[1].upper() or "HOME COACH" in tok[1].upper():
                parts.append('<div class="spacer-sm"></div>')
        elif tok[0] == "title":
            titles = tok[1]
            if titles[0].size < 26 or titles[0].italic:
                th = "<br>".join(esc(t.text) for t in titles)
                parts.append(f'<div class="h1-italic" style="font-size:38px;">{th}</div>')
            else:
                th = "<br>".join(esc(t.text) for t in titles)
                parts.append(f'<div class="h2">{th}</div>')
            parts.append('<div class="rule"></div>')
        elif tok[0] == "numbered":
            label, desc = tok[1], tok[2]
            num, title = parse_numbered_label(label)
            parts.append(
                f'<div class="numbered-block"><div class="numbered-title">'
                f'<span class="num">{esc(num)}</span> {esc(title)}</div></div>'
            )
            parts.extend(group_paragraphs(desc))
        elif tok[0] == "body":
            parts.extend(group_paragraphs(tok[1]))

    if sigue:
        parts.append(f"""<div class="next-link">
      <span class="arrow-label">{esc(sigue[0])}</span>
      <span class="arrow-title">{esc(sigue[1])}</span>
    </div>""")

    inner = "\n    ".join(parts)
    return f"""<!-- p{page_no} -->
<div class="page">
  <div class="content">
    {inner}
  </div>
  {banda(sec, page_no)}
</div>
"""


def build() -> str:
    doc = fitz.open(PDF)
    pages_html: list[str] = [cover_page(), legal_page()]

    for i in range(2, doc.page_count):
        page_no = i + 1
        lines = extract_lines(doc[i])
        if page_no == 3:
            pages_html.append(dedicatoria_page(lines))
        elif page_no == 9:
            pages_html.append(index_page_liderar())
        elif is_pull_page(lines):
            pages_html.append(pull_page(lines, page_no))
        elif is_mov_cover(lines):
            pages_html.append(mov_cover_page(lines, page_no))
        else:
            pages_html.append(content_page(lines, page_no))
    doc.close()

    bonus = BONUS.read_text(encoding="utf-8")
    s0 = bonus.index("<style>") + len("<style>")
    s1 = bonus.index("</style>")
    styles = bonus[s0:s1].split("<style>")[0]

    hub_body = """
<a class="hub-link hub-home" href="index.html">← Inicio</a>
<a class="hub-link hub-pdf" href="pdf/liderar.pdf" download>Descargar PDF</a>
"""
    body = "\n".join(pages_html)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>El arte de liderar tu hogar · Liviin</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Cormorant+SC:wght@300;400;500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
{styles}
</style>
</head>
<body>
{hub_body}
{body}
</body>
</html>
"""


def main() -> None:
    html_out = build()
    OUT.write_text(html_out, encoding="utf-8")
    print(f"OK {OUT} — {html_out.count('class=\"page')} páginas, {html_out.count('pull-page')} citas, {html_out.count('next-link')} sigue")


if __name__ == "__main__":
    main()
