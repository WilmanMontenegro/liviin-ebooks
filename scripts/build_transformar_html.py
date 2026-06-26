#!/usr/bin/env python3
"""PDF Transformar → HTML plantilla Liviin (bonus.html)."""
from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ebook_style import ebook_head_links
from html_blocks import (
    continues_pull_quote,
    is_firma_cierre_page,
    is_opening_lead,
    is_pull_page,
    is_pull_quote_group,
    is_section_subtitle,
    join_prose_html,
    join_prose_lines,
    paragraph_has_mixed_emphasis,
    mov_cover_subtitle_lines,
    pull_vlines_from_page,
    horizontal_filetes_from_page,
    render_section_label_html,
    render_firma_cierre_page,
    render_numeric_steps_page,
    render_opening_lead,
    render_pull_quote_html,
    render_tag_html,
    render_title_block,
    split_numeric_steps,
    fix_active_social_handles,
)
from pdf_text import (
    chars_to_line_text,
    collapse_orphan_caps,
    collapse_spaced,
    extract_line_text,
    fmt_inventory,
    fmt_page,
    fmt_structural,
    is_orphan_caps_line,
    merge_orphan_caps_lines,
    needs_gap_extract,
    normalize_label_part,
    numbered_caps_html,
    absorb_numbered_orphans,
    render_spans_inline_html,
    spans_need_inline_html,
)

ROOT = Path(__file__).resolve().parents[1]
from paths import PDF_DOWNLOAD_AS, TRANSFORMAR_PDF, WEB

PDF = TRANSFORMAR_PDF
OUT = WEB / "transformar.html"

MOVIMIENTOS = [
    (11, "01 · EL CAMBIO DE VISIÓN"),
    (22, "02 · LEJOS DE LA PERFECCIÓN"),
    (34, "03 · POR DÓNDE EMPEZAR"),
    (46, "04 · EL ORDEN REAL"),
    (61, "05 · TU EQUIPO DE TRANSFORMACIÓN"),
    (75, "06 · DE PROYECTO A HÁBITO"),
    (87, "07 · CUANDO TERMINA, EMPIEZA"),
    (94, "CIERRE"),
]

_KNOWN_FOOTER_KEYS: frozenset[str] | None = None


def _known_footer_keys() -> frozenset[str]:
    global _KNOWN_FOOTER_KEYS
    if _KNOWN_FOOTER_KEYS is None:
        keys = {_footer_key("INICIACIÓN"), _footer_key("ÍNDICE"), _footer_key("LIVIIN · EBOOK 01")}
        for _, label in MOVIMIENTOS:
            keys.add(_footer_key(label))
        _KNOWN_FOOTER_KEYS = frozenset(keys)
    return _KNOWN_FOOTER_KEYS

SIGUE_TITLES = {
    "02": "Lejos de la perfección",
    "03": "Por dónde empezar",
    "04": "El orden real",
    "05": "Tu equipo de transformación",
    "06": "De proyecto a hábito",
    "07": "Cuando termina, empieza",
    "CIERRE": "Tu casa te está esperando",
}

_PULL_VLINES: list[tuple[float, float]] = []
_H_FILETES: list[float] = []


@dataclass
class Line:
    text: str
    size: float
    y: float
    x: float = 0.0
    bold: bool = False
    italic: bool = False
    rich_html: str | None = None


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def parse_numbered_label(label: str) -> tuple[str, str]:
    if "·" in label:
        left, _, right = label.partition("·")
        return normalize_label_part(left), normalize_label_part(right)
    return "", normalize_label_part(label)


def fmt_caps(s: str) -> str:
    return esc(collapse_spaced(s))


def is_numbered_label(s: str) -> bool:
    return bool(re.match(r"^0\s*\d\s*·", s.strip()))


def _normalize_sigue_text(text: str) -> str:
    t = collapse_spaced(text)
    t = re.sub(r"ALMOVIMIENTO", "AL MOVIMIENTO", t, flags=re.I)
    t = re.sub(r"ALCIERRE", "AL CIERRE", t, flags=re.I)
    return t


def _is_sigue_line(text: str) -> bool:
    c = _normalize_sigue_text(text).upper()
    return bool(re.search(r"SIGUE\s+AL\s+(?:MOVIMIENTO|CIERRE)", c))


def is_tag_line(s: str, size: float) -> bool:
    if size > 10.5:
        return False
    t = s.strip()
    if is_numbered_label(t) or _is_sigue_line(t):
        return False
    return bool(re.search(r"(?:[A-ZÁÉÍÓÚ]\s){3,}", t))


def _is_section_label(ln: Line) -> bool:
    """PDF: etiqueta 8pt mayúsculas al margen izquierdo (≈x≤58)."""
    t = ln.text.strip()
    if ln.size > 9.5 or not t or is_numbered_label(t) or _is_sigue_line(t):
        return False
    if ln.x > 100:
        return False
    if not re.match(r"^[A-ZÁÉÍÓÚÑ0-9 ·—\-·\"']+$", t) or not any(c.isalpha() for c in t):
        return False
    words = collapse_spaced(t).split()
    if len(words) >= 3:
        return True
    if len(words) >= 2 and len(words[0]) >= 4:
        return True
    return len(words) == 1 and len(words[0]) >= 8


def _footer_key(s: str) -> str:
    return re.sub(r"[^\wáéíóúñ]", "", collapse_spaced(s).lower())


def is_margin_noise(ln: Line, page_h: float, page_no: int) -> bool:
    """Número de página y etiqueta de sección del pie PDF — ya van en .banda."""
    t = ln.text.strip()
    if re.fullmatch(r"\d{1,3}", t) and ln.size < 10:
        return True
    if ln.y <= page_h * 0.9:
        return False
    if _footer_key(t) in _known_footer_keys():
        return True
    if is_numbered_label(t) and ln.size <= 8.5:
        return True
    return False


def extract_lines(page: fitz.Page) -> list[Line]:
    out: list[Line] = []
    for b in page.get_text("rawdict")["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            spans = ln["spans"]
            if not spans:
                continue
            chars: list[dict] = []
            for sp in spans:
                chars.extend(sp.get("chars", []))
            raw = "".join(c["c"] for c in chars) if chars else ""
            text = extract_line_text(raw, chars) if chars else raw.strip()
            if not text.strip():
                continue
            rich = (
                render_spans_inline_html(spans, esc)
                if spans_need_inline_html(spans)
                else None
            )
            out.append(
                Line(
                    text=text.strip(),
                    size=max(s["size"] for s in spans),
                    y=min(s["bbox"][1] for s in spans),
                    x=min(s["bbox"][0] for s in spans),
                    bold=any(s["flags"] & 16 for s in spans),
                    italic=any(s["flags"] & 2 for s in spans),
                    rich_html=rich,
                )
            )
    out.sort(key=lambda x: x.y)
    return merge_orphan_caps_lines(out, is_numbered_label)


def section_for(page_no: int) -> str:
    if page_no <= 9:
        return "INICIACIÓN"
    if page_no == 10:
        return "ÍNDICE"
    for start, label in reversed(MOVIMIENTOS):
        if page_no >= start:
            return label
    return "INICIACIÓN"


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
    if is_opening_lead(g):
        return render_opening_lead(esc, g)
    if is_pull_quote_group(g, _PULL_VLINES):
        return [render_pull_quote_html(esc, " ".join(x.text for x in g))]
    text = " ".join(x.text for x in g)
    sizes = [x.size for x in g]
    if g[0].text.startswith("— MARÍA") or g[0].text.startswith("Interiorista y Home"):
        return ["""<div class="firma">
      <p class="con-carino">— María Teresa Espinosa</p>
      <p class="nombre">Interiorista y Home Coach · MTE</p>
    </div>"""]
    if any(x.rich_html for x in g) or paragraph_has_mixed_emphasis(g):
        return [f'<p class="body">{join_prose_html(g, esc)}</p>']
    if any(x.bold for x in g) and len(g) == 1:
        return [f'<p class="body"><em>{esc(text)}</em></p>']
    if all(x.italic for x in g) and all(9 <= s <= 12 for s in sizes):
        return [f'<p class="body body--italic">{esc(text)}</p>']
    return [f'<p class="body">{esc(text)}</p>']


def _group_prose(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    groups: list[list[Line]] = []
    cur: list[Line] = []
    prev_bottom: float | None = None
    for ln in lines:
        gap = 6 if cur and cur[-1].size <= 8.5 else 14
        if prev_bottom is not None:
            if ln.y + 12 < cur[-1].y:
                if cur:
                    groups.append(cur)
                    cur = []
            elif ln.y - prev_bottom > gap:
                if not (cur and continues_pull_quote(cur[-1], ln)):
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


# PDF: texto de viñeta ~x≈59; cuerpo fuera de lista ~x≈47 — no cortar por x (rompía saltos de línea)
BULLET_WRAP_Y_MAX = 34.0


def _extract_bullet_items(lines: list[Line], start: int) -> tuple[list[str], int]:
    """PDF: línea '•' + texto hasta el siguiente '•', hueco grande o margen de cuerpo."""
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
        if cur and ln.y - last_y > BULLET_WRAP_Y_MAX:
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
    numeric = split_numeric_steps(lines, _PULL_VLINES)
    if numeric:
        intro, items, tail = numeric
        return render_numeric_steps_page(
            esc, collapse_spaced, intro, items, tail, _is_section_label, _group_prose, _H_FILETES
        )
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


def parse_sigue_lines(lines: list[Line]) -> tuple[str, str] | None:
    for i, ln in enumerate(lines):
        if not _is_sigue_line(ln.text):
            continue
        label = _normalize_sigue_text(ln.text)
        m = re.search(
            r"SIGUE\s+AL\s+MOVIMIENTO\s+(\d{2})\s*→|SIGUE\s+AL\s+CIERRE\s*→",
            label,
            re.I,
        )
        if not m:
            continue
        title = ""
        if i + 1 < len(lines):
            nxt = lines[i + 1]
            if not _is_sigue_line(nxt.text) and not is_tag_line(nxt.text, nxt.size):
                title = nxt.text.strip()
        if "CIERRE" in m.group(0).upper():
            return ("SIGUE AL CIERRE →", title or SIGUE_TITLES["CIERRE"])
        return (f"SIGUE AL MOVIMIENTO {m.group(1)} →", title or SIGUE_TITLES.get(m.group(1), ""))
    return None


def arrow_label_html(label: str) -> str:
    t = label.rstrip()
    if t.endswith("→"):
        text = t[:-1].strip()
        return (
            f'<span class="arrow-label"><span class="arrow-label-text">{esc(text)}</span>'
            f'<span class="arrow-icon" aria-hidden="true">→</span></span>'
        )
    return f'<span class="arrow-label">{esc(t)}</span>'


def banda(section: str, num: int | str, show_num: bool = True) -> str:
    right = str(num) if show_num else ""
    return (
        f'  <div class="banda"><span class="banda-texto">{esc(section)}</span>'
        f'<span class="banda-texto">{right}</span></div>\n'
    )


def cover_page() -> str:
    return """<!-- PORTADA -->
<div class="page">
  <div class="foto-portada"><img src="assets/transformar-portada.jpg" alt=""></div>
  <div class="portada-content">
    <span class="portada-colofon">LIVIIN · EBOOK 02</span>
    <div class="portada-titulo">El arte de<br>transformar<br>tu hogar</div>
    <div class="portada-subtitulo">Una guía para dueñas que ya tienen la lista — y están listas para pasar de la idea al hacer.</div>
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
    <span class="tag">LIVIIN · EBOOK 02</span>
    <div class="h1" style="font-size:36px;margin-bottom:6px;">El arte de<br>transformar tu hogar</div>
    <div class="rule"></div>
    <div class="spacer-lg"></div>
    <p style="font-family:var(--sans);font-size:9px;letter-spacing:0.16em;color:var(--secundario);text-transform:uppercase;margin-bottom:6px;">MARÍA TERESA ESPINOSA</p>
    <p style="font-family:var(--serif-text);font-size:12px;font-style:italic;color:var(--secundario);">Interiorista y Home Coach · MTE</p>
    <div class="spacer-lg"></div>
    <p style="font-family:var(--sans);font-size:8.5px;letter-spacing:0.1em;color:var(--filete);text-transform:uppercase;">© LIVIIN · FOR BETTER LIVING</p>
    <p style="font-family:var(--serif-text);font-size:11px;font-style:italic;color:var(--filete);margin-top:4px;">Primera edición digital · 2026</p>
    <div class="spacer-md"></div>
    <p class="body" style="font-size:10px;color:var(--secundario);">Esta obra es la continuación de <em>El arte de liderar tu hogar</em> (Liviin · Ebook 01). Está pensada para acompañar a la dueña del hogar en el momento más difícil de toda transformación: el de pasar de la idea a la acción.</p>
  </div>
  <div class="banda"><span class="banda-texto">LIVIIN · EBOOK 02</span><span class="banda-texto"></span></div>
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
  <div class="content cierre-final">
    <div class="pull-page">
      <div class="pull-page-quote">{quote}</div>
      <span class="pull-page-attr">{fmt_caps(attr)}</span>
    </div>
  </div>
</div>
"""


def index_item_html(num: str, title: str, page: int | None = None) -> str:
    page_html = f'<span class="index-page">{fmt_page(page)}</span>' if page is not None else ""
    return (
        f'<div class="index-entry">'
        f'<div class="index-line"><span class="index-num">{esc(fmt_structural(num))}</span>'
        f'<span class="index-title">{esc(title)}</span></div>'
        f"{page_html}</div>"
    )


def parse_index_items(lines: list[Line]) -> tuple[list[tuple[str, str]], str]:
    items: list[tuple[str, str]] = []
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
    return items, " ".join(note)


def render_index_page(
    items: list[tuple[str, str]], section_pages: dict[str, int], note: str, folio: int
) -> str:
    items_html = "\n    ".join(
        index_item_html(n, t, section_pages.get(n)) for n, t in items
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
    <p class="body">{esc(note)}</p>
  </div>
  {banda("ÍNDICE", folio)}
</div>
"""


def _is_iniciacion_00(lines: list[Line]) -> bool:
    for ln in lines:
        t = collapse_spaced(ln.text).upper()
        if ln.size <= 10.5 and "INICIACI" in t and "00" in t:
            return True
    return False


def _mov_num_from_cover(lines: list[Line]) -> str | None:
    tag = mov_tag_text(lines)
    if not tag:
        return None
    m = re.search(r"MOVIMIENTO\s+(\d+)", tag, re.I)
    return f"{int(m.group(1)):02d}" if m else None


def _note_section_start(
    lines: list[Line],
    folio: int,
    section_pages: dict[str, int],
    pending_mov: str | None,
) -> str | None:
    if _is_iniciacion_00(lines):
        section_pages.setdefault("00", folio)
    if pending_mov is not None:
        section_pages.setdefault(pending_mov, folio)
        return None
    return pending_mov


def mov_cover_page(lines: list[Line], pdf_page_no: int) -> str:
    tag = mov_tag_text(lines)
    titles = [ln for ln in lines if ln.size >= 18 and not is_tag_line(ln.text, ln.size)]
    subs = mov_cover_subtitle_lines(lines, is_tag_line)
    title_html = "<br>".join(esc(collapse_spaced(t.text)) for t in titles)
    sub = esc(join_prose_lines(subs)) if subs else ""
    return f"""<!-- pdf p{pdf_page_no} movimiento -->
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


def _is_gracias_page(lines: list[Line]) -> bool:
    for ln in lines[:4]:
        if ln.size > 10.5:
            continue
        if "GRACIAS" in re.sub(r"\s+", "", ln.text.upper()):
            return True
    return False


def _render_gracias_page(lines: list[Line], pdf_page_no: int, folio: int) -> str:
    """PDF p.100: tag centrado + versos itálica en columna estrecha (no pull-quote)."""
    tag = "— GRACIAS —"
    body = [ln for ln in lines[1:] if ln.italic]
    groups: list[list[Line]] = []
    cur: list[Line] = []
    for ln in body:
        if cur and ln.y - cur[-1].y > 22:
            groups.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        groups.append(cur)
    verses = [
        f'    <p class="gracias-verse">{"<br>".join(esc(ln.text) for ln in g)}</p>'
        for g in groups
    ]
    inner = "\n".join([f'    <span class="gracias-tag">{esc(tag)}</span>', *verses])
    return f"""<!-- folio {folio} pdf p{pdf_page_no} -->
<div class="page">
  <div class="content gracias-page">
{inner}
  </div>
  {banda(section_for(pdf_page_no), folio)}
</div>
"""


def content_page(lines: list[Line], pdf_page_no: int, folio: int, fitz_page: fitz.Page) -> str:
    global _PULL_VLINES, _H_FILETES
    _PULL_VLINES = pull_vlines_from_page(fitz_page)
    _H_FILETES = horizontal_filetes_from_page(fitz_page)
    page_h = max((ln.y for ln in lines), default=0) + 25
    lines = [ln for ln in lines if not is_margin_noise(ln, page_h, pdf_page_no)]
    lines = merge_orphan_caps_lines(lines, is_numbered_label)
    if _is_gracias_page(lines):
        return _render_gracias_page(lines, pdf_page_no, folio)
    sec = section_for(pdf_page_no)
    sigue = parse_sigue_lines(lines)
    tokens: list[tuple] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _is_sigue_line(ln.text):
            break
        if is_tag_line(ln.text, ln.size):
            tokens.append(("tag", collapse_spaced(ln.text), ln.bold))
            i += 1
            continue
        if _is_section_label(ln):
            if ln.y < 120:
                tokens.append(("tag", collapse_spaced(ln.text), ln.bold))
            else:
                tokens.append(("section_label", ln))
            i += 1
            continue
        if is_numbered_label(ln.text):
            label = ln.text
            i += 1
            while i < len(lines) and is_orphan_caps_line(
                lines[i].text, lines[i].size, is_numbered_label
            ):
                label = f"{label.rstrip()} {collapse_orphan_caps(lines[i].text)}"
                i += 1
            desc: list[Line] = []
            while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 16 and not _is_sigue_line(lines[i].text):
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
            subtitle = lines[i] if i < len(lines) and is_section_subtitle(lines[i]) else None
            if subtitle is not None:
                i += 1
            tokens.append(("title", titles, subtitle))
            continue
        if ln.text.startswith("—") and ln.size < 12:
            i += 1
            continue
        chunk = [ln]
        i += 1
        while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 16 and not _is_sigue_line(lines[i].text) and not _is_section_label(lines[i]) and not (lines[i].text.startswith("—") and lines[i].size < 12):
            chunk.append(lines[i])
            i += 1
        tokens.append(("body", chunk))

    parts: list[str] = []
    for tok in tokens:
        if tok[0] == "tag":
            parts.append(render_tag_html(esc, tok[1], bold=tok[2]))
            if "CIERRE DEL MOVIMIENTO" in tok[1].upper() or "HOME COACH" in tok[1].upper():
                parts.append('<div class="spacer-sm"></div>')
        elif tok[0] == "title":
            parts.extend(render_title_block(esc, tok[1], tok[2]))
        elif tok[0] == "section_label":
            parts.append(render_section_label_html(esc, tok[1].text, tok[1].y, _H_FILETES))
        elif tok[0] == "numbered":
            label, desc = absorb_numbered_orphans(tok[1], tok[2], is_numbered_label)
            num, title = parse_numbered_label(label)
            parts.append(
                f'<div class="numbered-block"><div class="numbered-title">'
                f'{numbered_caps_html(num, title)}</div></div>'
            )
            parts.extend(group_paragraphs(desc))
        elif tok[0] == "body":
            chunk = list(tok[1])
            if (
                chunk
                and parts
                and "numbered-title" in parts[-1]
                and is_orphan_caps_line(chunk[0].text, chunk[0].size, is_numbered_label)
            ):
                orphan = esc(collapse_orphan_caps(chunk[0].text))
                parts[-1] = parts[-1].replace(
                    "</div></div>", f" {orphan}</div></div>", 1
                )
                chunk = chunk[1:]
            if chunk:
                parts.extend(group_paragraphs(chunk))

    if sigue:
        parts.append(f"""<div class="next-link">
      {arrow_label_html(sigue[0])}
      <span class="arrow-title">{esc(sigue[1])}</span>
    </div>""")

    inner = "\n    ".join(parts)
    return f"""<!-- folio {folio} pdf p{pdf_page_no} -->
<div class="page">
  <div class="content">
    {inner}
  </div>
  {banda(sec, folio)}
</div>
"""


PDF_CONTENT_H = 648.0


def _is_overview_page(lines: list[Line]) -> bool:
    return sum(1 for ln in lines if is_numbered_label(ln.text)) >= 2


def _starts_new_section(lines: list[Line]) -> bool:
    for ln in lines[:4]:
        if is_tag_line(ln.text, ln.size):
            t = collapse_spaced(ln.text).upper()
            if "MOVIMIENTO" in t or "CIERRE" in t or "ÍNDICE" in t or "INICIACI" in t:
                return True
        if ln.size >= 22 and not ln.italic:
            return True
    return False


def _is_sparse_continuation(next_lines: list[Line]) -> bool:
    """PDF siguiente muy liviana, mismo hilo — sin tag/título nuevo arriba."""
    if not next_lines or _starts_new_section(next_lines):
        return False
    ymax = max(ln.y for ln in next_lines)
    if ymax > 220:
        return False
    # ponytail: pull-quote multi-línea infla len; ymax ≈ altura real en el PDF
    return len(next_lines) <= 14


def _is_list_continuation(next_lines: list[Line]) -> bool:
    """PDF siguiente sigue una lista — sin sección nueva arriba."""
    if not next_lines or _starts_new_section(next_lines):
        return False
    if not any(ln.text.strip() == "•" for ln in next_lines[:8]):
        return False
    ymax = max(ln.y for ln in next_lines)
    if ymax > 320:
        return False
    return len(next_lines) <= 20


def _offset_lines(lines: list[Line], dy: float) -> list[Line]:
    return [
        Line(ln.text, ln.size, ln.y + dy, ln.x, ln.bold, ln.italic) for ln in lines
    ]


def _paragraph_split_y(lines: list[Line], target: float = 415.0) -> float | None:
    """Corte en hueco de párrafo cerca de target — nunca a mitad de frase."""
    split_at: list[float] = []
    prev_bottom: float | None = None
    for ln in lines:
        if prev_bottom is not None and ln.y - prev_bottom > 14:
            split_at.append(ln.y)
        prev_bottom = ln.y + max(ln.size * 0.35, 8)
    best: float | None = None
    best_dist = float("inf")
    for y in split_at:
        early = sum(1 for ln in lines if ln.y < y)
        late = sum(1 for ln in lines if ln.y >= y)
        if early < 8 or late < 2:
            continue
        if any(is_numbered_label(ln.text) for ln in lines if ln.y >= y):
            continue
        dist = abs(y - target)
        if dist < best_dist:
            best_dist = dist
            best = y
    return best


def _try_merge_sparse_next(
    lines: list[Line], page_no: int, next_lines: list[Line]
) -> tuple[list[Line], bool]:
    """PDF deja hueco abajo y la siguiente es liviana → un solo HTML."""
    if page_no < 4 or not lines or not next_lines:
        return lines, False
    room = PDF_CONTENT_H - max(ln.y for ln in lines)
    dy = max(ln.y for ln in lines) - min(ln.y for ln in next_lines) + 28
    tail = _offset_lines(next_lines, dy)
    if _is_overview_page(lines) and _is_overview_page(next_lines):
        if room >= 100 and max(ln.y for ln in next_lines) <= 400:
            return lines + tail, True
        return lines, False
    if _is_sparse_continuation(next_lines) or _is_list_continuation(next_lines):
        return lines + tail, True
    return lines, False


def _split_dense_tail(
    lines: list[Line], page_no: int, next_lines: list[Line] | None
) -> tuple[list[Line], list[Line]]:
    """PDF p.4 llena el frame HTML; si la siguiente es liviana, adelanta cola."""
    if not lines or page_no < 4:
        return lines, []
    if _is_overview_page(lines):
        return lines, []
    if next_lines is not None and (
        _is_sparse_continuation(next_lines) or _is_list_continuation(next_lines)
    ):
        return lines, []
    if max(ln.y for ln in lines) < 475:
        return lines, []
    if next_lines is not None and len(next_lines) > 6:
        return lines, []
    cut = _paragraph_split_y(lines)
    if cut is None:
        return lines, []
    early = [ln for ln in lines if ln.y < cut]
    late = [ln for ln in lines if ln.y >= cut]
    if len(early) < 8 or len(late) < 2:
        return lines, []
    return early, late


def build() -> str:
    doc = fitz.open(PDF)
    pages_before: list[str] = [cover_page(), legal_page()]
    pages_after: list[str] = []
    carry: list[Line] = []
    skip_indices: set[int] = set()
    section_pages: dict[str, int] = {}
    pending_mov: str | None = None
    index_items: list[tuple[str, str]] = []
    index_note = ""
    past_index_slot = False
    index_folio: int | None = None
    folio = 2  # portada + legal

    for i in range(2, doc.page_count):
        if i in skip_indices:
            continue
        page_no = i + 1
        raw = extract_lines(doc[i])
        next_raw = extract_lines(doc[i + 1]) if i + 1 < doc.page_count else None
        if carry:
            lines = carry + raw
            carry = []
            merged_this = False
        else:
            lines = raw
            merged_this = False
            if next_raw is not None and page_no not in (3, 10):
                merged, skip = _try_merge_sparse_next(raw, page_no, next_raw)
                if skip:
                    lines = merged
                    skip_indices.add(i + 1)
                    merged_this = True
        if page_no == 10:
            index_items, index_note = parse_index_items(lines)
            index_folio = len(pages_before) + 1
            past_index_slot = True
            continue
        folio += 1
        if past_index_slot and index_folio is not None and folio == index_folio:
            folio += 1
        if page_no == 3:
            pages_before.append(dedicatoria_page(lines))
        elif is_firma_cierre_page(lines):
            html = render_firma_cierre_page(esc, lines, page_no, folio)
            (pages_after if past_index_slot else pages_before).append(html)
        elif is_pull_page(lines):
            html = pull_page(lines, page_no)
            (pages_after if past_index_slot else pages_before).append(html)
        elif is_mov_cover(lines):
            pending_mov = _mov_num_from_cover(lines)
            html = mov_cover_page(lines, page_no)
            (pages_after if past_index_slot else pages_before).append(html)
        else:
            if not merged_this:
                lines, carry = _split_dense_tail(lines, page_no, next_raw)
            pending_mov = _note_section_start(lines, folio, section_pages, pending_mov)
            html = content_page(lines, page_no, folio, doc[i])
            (pages_after if past_index_slot else pages_before).append(html)
    doc.close()

    if index_folio is None:
        index_folio = len(pages_before) + 1
    pages_html = (
        pages_before
        + [render_index_page(index_items, section_pages, index_note, index_folio)]
        + pages_after
    )

    hub_body = f"""
<a class="hub-link hub-home" href="index.html"><span class="hub-link__arrow" aria-hidden="true"></span><span class="hub-link__label">Inicio</span></a>
<a class="hub-link hub-pdf" href="pdf/transformar.pdf" download="{PDF_DOWNLOAD_AS["transformar.pdf"]}"><span class="hub-link__label">Descargar PDF</span></a>
"""
    body = "\n".join(pages_html)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>El arte de transformar tu hogar · Liviin</title>
{ebook_head_links()}
</head>
<body>
{hub_body}
{body}
</body>
</html>
"""


def main() -> None:
    html_out = fix_active_social_handles(build())
    OUT.write_text(html_out, encoding="utf-8")
    print(f"OK {OUT} — {html_out.count('class=\"page')} páginas, {html_out.count('pull-page')} citas, {html_out.count('next-link')} sigue")


if __name__ == "__main__":
    main()
