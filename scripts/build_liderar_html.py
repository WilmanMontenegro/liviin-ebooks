#!/usr/bin/env python3
"""PDF Liderar → HTML plantilla Liviin (bonus.html)."""
from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html_blocks import (
    continues_pull_quote,
    is_firma_cierre_page,
    is_opening_lead,
    is_pull_quote_group,
    is_section_subtitle,
    render_firma_cierre_page,
    render_numeric_steps_page,
    render_opening_lead,
    render_tag_html,
    render_title_block,
    split_numeric_steps,
)
from ebook_style import ebook_head_links
from pdf_text import (
    chars_to_line_text,
    collapse_spaced,
    extract_line_text,
    fmt_inventory,
    fmt_structural,
    merge_orphan_caps_lines,
    needs_gap_extract,
    normalize_label_part,
    numbered_caps_html,
    is_orphan_caps_line,
    absorb_numbered_orphans,
    collapse_orphan_caps,
)

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "4_El_arte_de_liderar_tu_hogar_v11_FINAL.pdf"
OUT = ROOT / "web" / "liderar.html"

MOVIMIENTOS = [
    (11, "01 · LA FILOSOFÍA"),
    (24, "02 · CONOCE TU CASA"),
    (37, "03 · EQUIPO"),
    (58, "04 · ARMONÍA"),
    (67, "05 · MI HISTORIA"),
    (74, "BONUS · CONVERSACIONES"),
    (87, "CIERRE"),
    (88, "BONUS"),
]

INDEX_ITEMS = [
    ("00", "Iniciación · De mí para ti"),
    ("01", "La filosofía del hogar bien llevado"),
    ("02", "Conoce tu casa antes de delegarla"),
    ("03", "Construir el equipo"),
    ("04", "Sostener la armonía en el tiempo"),
    ("05", "Bonus · Conversaciones esenciales"),
    ("06", "Cierre · El hogar como reflejo"),
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
    x: float = 0.0
    bold: bool = False
    italic: bool = False


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


_AREA_ITEM = re.compile(r"^(\d{1,2})\s{2,}(.+)$")


def _is_section_label(ln: Line) -> bool:
    """PDF: etiqueta 8pt mayúsculas antes del título de sección."""
    t = ln.text.strip()
    if ln.size > 9.5 or not t or is_numbered_label(t) or _is_sigue_line(t):
        return False
    return bool(re.match(r"^[A-ZÁÉÍÓÚÑ0-9 ·—\-·\"']+$", t)) and any(c.isalpha() for c in t)


def _parse_area_item(text: str) -> tuple[int, str] | None:
    m = _AREA_ITEM.match(text.strip())
    return (int(m.group(1)), m.group(2).strip()) if m else None


def _is_area_map_line(ln: Line) -> bool:
    return _parse_area_item(ln.text) is not None


def _render_area_map_block(lines: list[Line]) -> str:
    by_y: dict[int, list[Line]] = {}
    for ln in lines:
        by_y.setdefault(round(ln.y), []).append(ln)
    cells: list[str] = []
    for y in sorted(by_y):
        for ln in sorted(by_y[y], key=lambda l: l.x):
            p = _parse_area_item(ln.text)
            if not p:
                continue
            n, label = p
            cells.append(
                f'<div class="area-item"><span class="area-num">{fmt_inventory(n)}</span>'
                f'<span class="area-label">{esc(label)}</span></div>'
            )
    return f'<div class="area-grid">{"".join(cells)}</div>'


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
            out.append(
                Line(
                    text=text.strip(),
                    size=max(s["size"] for s in spans),
                    y=min(s["bbox"][1] for s in spans),
                    x=min(s["bbox"][0] for s in spans),
                    bold=any(s["flags"] & 16 for s in spans),
                    italic=any(s["flags"] & 2 for s in spans),
                )
            )
    out.sort(key=lambda x: (x.y, x.x))
    return merge_orphan_caps_lines(out, is_numbered_label)


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
        if not compact.startswith("MOVIMIENTO"):
            continue
        if "CIERRE" in compact:
            return "MOVIMIENTO CIERRE"
        if "BONUS" in compact:
            return "MOVIMIENTO BONUS"
        m = re.search(r"0?(\d+)", compact)
        if m:
            return f"MOVIMIENTO {m.group(1).zfill(2)}"
    return ""


def is_mov_cover(lines: list[Line]) -> bool:
    if not mov_tag_text(lines):
        return False
    extras = sum(1 for ln in lines if ln.size >= 10 and not is_tag_line(ln.text, ln.size))
    return extras <= 5


def _is_iniciacion_00(lines: list[Line]) -> bool:
    for ln in lines:
        t = collapse_spaced(ln.text).upper()
        if ln.size <= 10.5 and "INICIACI" in t and "00" in t:
            return True
    return False


def _mov_key_from_cover(lines: list[Line]) -> str | None:
    tag = mov_tag_text(lines)
    if not tag:
        return None
    if "CIERRE" in tag.upper():
        return "06"
    if "BONUS" in tag.upper():
        return "05"
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


def _render_prose_group(g: list[Line]) -> list[str]:
    if is_opening_lead(g):
        return render_opening_lead(esc, g)
    if is_pull_quote_group(g):
        return [f'<div class="pull-quote"><p>{esc(" ".join(x.text for x in g))}</p></div>']
    text = " ".join(x.text for x in g)
    sizes = [x.size for x in g]
    if all(x.italic for x in g) and all(s >= 13.5 for s in sizes):
        return [f'<p class="closing-lead">{esc(text)}</p>']
    if any(x.bold for x in g) and len(g) == 1:
        return [f'<p class="body"><strong>{esc(text)}</strong></p>']
    if g[0].text.startswith("— MARÍA") or g[0].text.startswith("Interiorista y Home"):
        return ["""<div class="firma">
      <p class="con-carino">— María Teresa Espinosa</p>
      <p class="nombre">Interiorista y Home Coach · MTE</p>
    </div>"""]
    if all(x.italic for x in g) and all(9 <= s <= 12 for s in sizes):
        return [f'<p class="body body--italic">{esc(text)}</p>']
    return [f'<p class="body">{esc(text)}</p>']


def _group_prose(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    parts: list[str] = []
    i = 0
    while i < len(lines):
        if _is_area_map_line(lines[i]):
            area: list[Line] = []
            while i < len(lines) and _is_area_map_line(lines[i]):
                area.append(lines[i])
                i += 1
            parts.append(_render_area_map_block(area))
            continue
        j = i
        while j < len(lines) and not _is_area_map_line(lines[j]):
            j += 1
        parts.extend(_group_prose_plain(lines[i:j]))
        i = j
    return parts


_REMINDER_LABELS = frozenset({"RECORDATORIO", "ANTICIPO", "DESCARGA DIRECTA"})


def _is_reminder_callout(label: Line, body: list[Line]) -> bool:
    key = re.sub(r"\s+", "", collapse_spaced(label.text).upper())
    if key not in _REMINDER_LABELS:
        return False
    text = " ".join(ln.text.strip() for ln in body)
    return bool(text) and len(text) < 280


def _render_label_callout(label: Line, body: list[Line]) -> str:
    text = " ".join(ln.text.strip() for ln in body)
    return (
        f'<div class="caja-crema reminder-block">'
        f'<p class="section-label">{esc(collapse_spaced(label.text))}</p>'
        f'<p class="reminder-text">{esc(text)}</p></div>'
    )


def _split_label_callout(
    lines: list[Line],
) -> tuple[list[Line], Line, list[Line], list[Line]] | None:
    """PDF: etiqueta 8pt (RECORDATORIO) + texto debajo en caja crema."""
    for i, ln in enumerate(lines):
        if not _is_section_label(ln):
            continue
        j = i + 1
        body: list[Line] = []
        while j < len(lines) and lines[j].size < 12 and not _is_sigue_line(lines[j].text):
            body.append(lines[j])
            j += 1
        if not body or not _is_reminder_callout(ln, body):
            continue
        return lines[:i], ln, body, lines[j:]
    return None


def _group_prose_plain(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    callout = _split_label_callout(lines)
    if callout:
        intro, label, body, tail = callout
        return (
            _group_prose_plain(intro)
            + [_render_label_callout(label, body)]
            + _group_prose_plain(tail)
        )
    groups: list[list[Line]] = []
    cur: list[Line] = []
    prev_bottom: float | None = None
    for ln in lines:
        gap = 6 if cur and cur[-1].size <= 8.5 else 14
        if prev_bottom is not None and ln.y - prev_bottom > gap:
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


# PDF: texto de lista va ~x≥58; cuerpo al margen ~x≤47
BULLET_TEXT_X_MIN = 85.0


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
        if cur and (ln.y - last_y > 34 or ln.x < BULLET_TEXT_X_MIN):
            break
        cur.append(ln.text)
        last_y = ln.y
        i += 1
    if cur:
        items.append(" ".join(cur))
    return items, i


_ORDINAL_ITEM = re.compile(
    r"^(Uno|Dos|Tres|Cuatro|Cinco|Seis|Siete|Ocho|Nueve|Diez)\.\s*(.*)",
    re.I,
)


def _is_ordinal_start(ln: Line) -> bool:
    return bool(_ORDINAL_ITEM.match(ln.text.strip()))


def _split_ordinal_items(lines: list[Line]) -> tuple[list[Line], list[tuple[str, str]]] | None:
    """PDF: párrafos 'Uno. …' 'Dos. …' en líneas separadas."""
    starts = [i for i, ln in enumerate(lines) if _is_ordinal_start(ln)]
    if len(starts) < 2:
        return None
    intro = lines[: starts[0]]
    items: list[tuple[str, str]] = []
    for j, si in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        chunk = lines[si:end]
        m = _ORDINAL_ITEM.match(chunk[0].text.strip())
        if not m:
            continue
        label = m.group(1).capitalize()
        parts = [m.group(2).strip()] if m.group(2).strip() else []
        parts.extend(ln.text.strip() for ln in chunk[1:])
        items.append((label, " ".join(parts)))
    return intro, items if len(items) >= 2 else None


def _render_ordinal_block(intro: list[Line], items: list[tuple[str, str]]) -> list[str]:
    parts = _group_prose_plain(intro) if intro else []
    blocks = "".join(
        f'<div class="discovery-item">'
        f'<span class="discovery-num">{esc(fmt_structural(i + 1))}</span>'
        f'<p class="discovery-text">{esc(text)}</p></div>'
        for i, (label, text) in enumerate(items)
    )
    parts.append(f'<div class="discovery-list">{blocks}</div>')
    return parts


def _is_step_num(ln: Line) -> bool:
    return bool(re.fullmatch(r"\d{2}", ln.text.strip())) and 10 <= ln.size <= 12 and ln.x < 65


def _same_row(a: Line, b: Line) -> bool:
    return abs(a.y - b.y) <= 1.0


def _title_on_step_row(lines: list[Line], step_i: int) -> tuple[int, str] | None:
    for j, ln in enumerate(lines):
        if j == step_i or not _same_row(ln, lines[step_i]) or ln.x <= lines[step_i].x + 15:
            continue
        return j, ln.text.strip()
    return None


def _split_desc_tail(desc_idxs: list[int], lines: list[Line], gap: float = 35) -> tuple[list[int], list[int]]:
    if len(desc_idxs) < 2:
        return desc_idxs, []
    ordered = sorted(desc_idxs, key=lambda k: lines[k].y)
    for i in range(len(ordered) - 1, 0, -1):
        if lines[ordered[i]].y - lines[ordered[i - 1]].y > gap:
            return ordered[:i], ordered[i:]
    return ordered, []


def _split_step_blocks(lines: list[Line]) -> tuple[list[Line], list[tuple[str, str, str]], list[Line]] | None:
    """PDF: '01' + título en la misma fila, cuerpo indentado debajo (p.39)."""
    step_idxs = [i for i, ln in enumerate(lines) if _is_step_num(ln)]
    if len(step_idxs) < 2:
        return None
    pairs = [_title_on_step_row(lines, i) for i in step_idxs]
    if not all(pairs):
        return None

    items: list[tuple[str, str, str]] = []
    consumed: set[int] = set()
    for si, step_i in enumerate(step_idxs):
        title_j, title = pairs[si]
        consumed.add(step_i)
        consumed.add(title_j)
        y_lo = lines[step_i].y + 0.5
        y_hi = lines[step_idxs[si + 1]].y - 0.5 if si + 1 < len(step_idxs) else float("inf")
        desc_idxs = [
            k
            for k in range(len(lines))
            if k not in consumed and y_lo < lines[k].y < y_hi
        ]
        if si + 1 >= len(step_idxs):
            desc_idxs, _ = _split_desc_tail(desc_idxs, lines)
        desc = " ".join(lines[k].text.strip() for k in desc_idxs)
        consumed.update(desc_idxs)
        items.append((lines[step_i].text.strip(), title, desc))

    intro = [lines[i] for i in range(step_idxs[0]) if i not in consumed]
    tail = [lines[k] for k in range(step_idxs[0], len(lines)) if k not in consumed]
    return intro, items, tail


def _has_question_items(lines: list[Line]) -> bool:
    step_idxs = [i for i, ln in enumerate(lines) if _is_step_num(ln)]
    if len(step_idxs) < 2:
        return False
    for si, step_i in enumerate(step_idxs):
        end = step_idxs[si + 1] if si + 1 < len(step_idxs) else min(step_i + 5, len(lines))
        for k in range(step_i + 1, end):
            if lines[k].text.strip().startswith('"'):
                return True
    return False


def _split_question_blocks(lines: list[Line]) -> tuple[list[Line], list[tuple[str, str, str]], list[Line]] | None:
    """PDF p.42: 01 + pregunta entre comillas, párrafo 'Revela…' debajo."""
    if not _has_question_items(lines):
        return None
    step_idxs = [i for i, ln in enumerate(lines) if _is_step_num(ln)]
    items: list[tuple[str, str, str]] = []
    consumed: set[int] = set()
    for si, step_i in enumerate(step_idxs):
        consumed.add(step_i)
        end = step_idxs[si + 1] if si + 1 < len(step_idxs) else len(lines)
        q_parts: list[str] = []
        insight_parts: list[str] = []
        for k in range(step_i + 1, end):
            t = lines[k].text.strip()
            if t.startswith("Revela"):
                insight_parts.append(t)
            elif insight_parts:
                insight_parts.append(t)
            else:
                q_parts.append(t)
            consumed.add(k)
        if not q_parts:
            return None
        items.append((lines[step_i].text.strip(), " ".join(q_parts), " ".join(insight_parts)))
    intro = [lines[i] for i in range(step_idxs[0]) if i not in consumed]
    tail = [lines[k] for k in range(step_idxs[0], len(lines)) if k not in consumed]
    return intro, items, tail


def _render_step_block_page(
    intro: list[Line], items: list[tuple[str, str, str]], tail: list[Line]
) -> list[str]:
    parts = _group_prose_plain(intro)
    blocks = "".join(
        f'<div class="step-item"><div class="step-head">'
        f'<span class="step-num">{esc(fmt_structural(num))}</span>'
        f'<span class="step-title">{esc(title)}</span></div>'
        f'<p class="step-desc">{esc(desc)}</p></div>'
        for num, title, desc in items
    )
    parts.append(f'<div class="step-list">{blocks}</div>')
    for ln in tail:
        cls = "body step-closing" if ln.italic else "body"
        parts.append(f'<p class="{cls}">{esc(ln.text)}</p>')
    return parts


def _render_question_block_page(
    intro: list[Line], items: list[tuple[str, str, str]], tail: list[Line]
) -> list[str]:
    parts = _group_prose_plain(intro)
    blocks = "".join(
        f'<div class="step-item step-item--question">'
        f'<div class="step-question-row">'
        f'<span class="step-num">{esc(fmt_structural(num))}</span>'
        f'<p class="step-question">{esc(question)}</p></div>'
        f'<p class="step-insight">{esc(insight)}</p></div>'
        for num, question, insight in items
    )
    parts.append(f'<div class="step-list step-list--questions">{blocks}</div>')
    for ln in tail:
        parts.append(f'<p class="body">{esc(ln.text)}</p>')
    return parts


def _is_overview_num(ln: Line) -> bool:
    """PDF Liderar: línea suelta '01' antes del texto del ítem."""
    return bool(re.fullmatch(r"\d{2}", ln.text.strip())) and 10.5 <= ln.size <= 12


def _overview_item_html(num: str, text: str) -> list[str]:
    full = text.strip()
    if " — " in full:
        title, _, rest = full.partition(" — ")
        desc = "— " + rest
    elif "—" in full:
        idx = full.index("—")
        title, desc = full[:idx].strip(), full[idx:].strip()
    else:
        title, desc = full, ""
    out = [
        f'<div class="index-line overview-line">'
        f'<span class="index-num">{esc(fmt_structural(num))}</span>'
        f'<span class="index-title">{esc(title)}</span></div>'
    ]
    if desc:
        out.append(f'<p class="body" style="margin-left:28px;">{esc(desc)}</p>')
    return out


def index_item_html(num: str, title: str, page: int | None = None) -> str:
    page_html = f'<span class="index-page">{page:02d}</span>' if page is not None else ""
    return (
        f'<div class="index-entry">'
        f'<div class="index-line"><span class="index-num">{esc(fmt_structural(num))}</span>'
        f'<span class="index-title">{esc(title)}</span></div>'
        f"{page_html}</div>"
    )


def group_paragraphs(lines: list[Line]) -> list[str]:
    if not lines:
        return []
    ordinal = _split_ordinal_items(lines)
    if ordinal:
        intro, items = ordinal
        return _render_ordinal_block(intro, items)
    numeric = split_numeric_steps(lines)
    if numeric:
        intro, items, tail = numeric
        return render_numeric_steps_page(
            esc, collapse_spaced, intro, items, tail, _is_section_label, _group_prose_plain
        )
    steps = _split_step_blocks(lines)
    if steps:
        intro, items, tail = steps
        return _render_step_block_page(intro, items, tail)
    questions = _split_question_blocks(lines)
    if questions:
        intro, items, tail = questions
        return _render_question_block_page(intro, items, tail)
    has_bullets = any(ln.text.strip() == "•" for ln in lines)
    has_overview = any(_is_overview_num(ln) for ln in lines)
    if not has_bullets and not has_overview:
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
        if _is_overview_num(lines[i]):
            num = lines[i].text.strip()
            i += 1
            chunk: list[str] = []
            while i < len(lines) and lines[i].text.strip() != "•" and not _is_overview_num(lines[i]):
                chunk.append(lines[i].text)
                i += 1
            parts.extend(_overview_item_html(num, " ".join(chunk)))
            continue
        j = i
        while j < len(lines) and lines[j].text.strip() != "•" and not _is_overview_num(lines[j]):
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
  <div class="content cierre-final">
    <div class="pull-page">
      <div class="pull-page-quote">{quote}</div>
      <span class="pull-page-attr">{fmt_caps(attr)}</span>
    </div>
  </div>
</div>
"""


def index_page_liderar(section_pages: dict[str, int], folio: int) -> str:
    items_html = "\n    ".join(
        index_item_html(n, t, section_pages.get(n)) for n, t in INDEX_ITEMS
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
  {banda("ÍNDICE", folio)}
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
        f'<div class="numbered-block"><div class="numbered-title">{numbered_caps_html(n, t)}</div></div>'
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


def _is_section_subtitle(ln: Line) -> bool:
    return is_section_subtitle(ln)


def mov_cover_page(lines: list[Line], page_no: int) -> str:
    tag = mov_tag_text(lines)
    titles = [ln for ln in lines if ln.size >= 18 and not is_tag_line(ln.text, ln.size)]
    subs = [ln for ln in lines if 10 <= ln.size <= 14 and not is_tag_line(ln.text, ln.size)]
    title_html = "<br>".join(esc(collapse_spaced(t.text)) for t in titles)
    sub = esc(collapse_spaced(subs[-1].text)) if subs else ""
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


def content_page(lines: list[Line], pdf_page_no: int, folio: int) -> str:
    page_h = max((ln.y for ln in lines), default=0) + 25
    lines = [ln for ln in lines if not is_margin_noise(ln, page_h, pdf_page_no)]
    lines = merge_orphan_caps_lines(lines, is_numbered_label)
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
            tokens.append(("tag", collapse_spaced(ln.text), ln.bold))
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
            while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 15.5 and not _is_sigue_line(lines[i].text):
                desc.append(lines[i])
                i += 1
            tokens.append(("numbered", label, desc))
            continue
        if ln.size >= 15.5 and not is_tag_line(ln.text, ln.size):
            titles = [ln]
            i += 1
            while i < len(lines) and lines[i].size >= 15.5 and not is_tag_line(lines[i].text, lines[i].size):
                titles.append(lines[i])
                i += 1
            subtitle = lines[i] if i < len(lines) and _is_section_subtitle(lines[i]) else None
            if subtitle is not None:
                i += 1
            tokens.append(("title", titles, subtitle))
            continue
        if ln.text.startswith("—") and ln.size < 12:
            i += 1
            continue
        chunk = [ln]
        i += 1
        while i < len(lines) and not is_tag_line(lines[i].text, lines[i].size) and not is_numbered_label(lines[i].text) and lines[i].size < 15.5 and not _is_sigue_line(lines[i].text) and not (lines[i].text.startswith("—") and lines[i].size < 12):
            chunk.append(lines[i])
            i += 1
        tokens.append(("body", chunk))

    parts: list[str] = []
    for tok in tokens:
        if tok[0] == "tag":
            parts.append(render_tag_html(esc, tok[1], bold=tok[2]))
            if "CIERRE DEL MOVIMIENTO" in tok[1].upper():
                parts.append('<div class="spacer-sm"></div>')
        elif tok[0] == "title":
            parts.extend(render_title_block(esc, tok[1], tok[2]))
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
    content_cls = "content"
    if re.search(r'<span class="tag">[^<]*GRACIAS', inner, re.I):
        content_cls = "content gracias-lead-page"
    return f"""<!-- folio {folio} pdf p{pdf_page_no} -->
<div class="page">
  <div class="{content_cls}">
    {inner}
  </div>
  {banda(sec, folio)}
</div>
"""


def build() -> str:
    doc = fitz.open(PDF)
    pages_before: list[str] = [cover_page(), legal_page()]
    pages_after: list[str] = []
    section_pages: dict[str, int] = {}
    pending_mov: str | None = None
    index_folio: int | None = None
    past_index_slot = False
    folio = 2

    for i in range(2, doc.page_count):
        page_no = i + 1
        lines = extract_lines(doc[i])
        if page_no == 9:
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
            pending_mov = _mov_key_from_cover(lines)
            html = mov_cover_page(lines, page_no)
            (pages_after if past_index_slot else pages_before).append(html)
        else:
            pending_mov = _note_section_start(lines, folio, section_pages, pending_mov)
            html = content_page(lines, page_no, folio)
            (pages_after if past_index_slot else pages_before).append(html)
    doc.close()

    if index_folio is None:
        index_folio = len(pages_before) + 1
    pages_html = (
        pages_before
        + [index_page_liderar(section_pages, index_folio)]
        + pages_after
    )

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
{ebook_head_links()}
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
