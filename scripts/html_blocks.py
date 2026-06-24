"""Bloques HTML compartidos entre builds PDF → ebook."""
from __future__ import annotations

import re
from typing import Callable, Protocol

from pdf_text import collapse_spaced

_NUMERIC_STEP = re.compile(r"^(\d+)\.\s*(.*)")


class TextLine(Protocol):
    text: str
    size: float
    italic: bool


def is_section_subtitle(ln: TextLine) -> bool:
    return 14 <= ln.size <= 16 and ln.italic


def render_title_block(
    esc: Callable[[str], str],
    titles: list[TextLine],
    subtitle: TextLine | None,
) -> list[str]:
    t0 = titles[0]
    if t0.italic or t0.size >= 26:
        th = "<br>".join(esc(collapse_spaced(t.text)) for t in titles)
        return [
            f'<div class="h1-italic" style="font-size:38px;">{th}</div>',
            '<div class="rule"></div>',
        ]
    th = "<br>".join(esc(collapse_spaced(t.text)) for t in titles)
    # ponytail: dígitos en Cormorant SC se ven de otra fuente; PDF = Liberation Serif (≈ h2-section)
    section_style = subtitle is not None or any(
        re.search(r"\d", collapse_spaced(t.text)) for t in titles
    )
    h2_cls = "h2 h2-section" if section_style else "h2"
    if subtitle is not None:
        return [
            f'<div class="{h2_cls}">{th}</div>',
            f'<p class="section-subtitle">{esc(collapse_spaced(subtitle.text))}</p>',
            '<div class="rule"></div>',
        ]
    return [f'<div class="{h2_cls}">{th}</div>', '<div class="rule"></div>']


def is_numeric_step_line(text: str) -> bool:
    return bool(_NUMERIC_STEP.match(text.strip()))


def parse_numeric_step(text: str) -> tuple[str, str] | None:
    m = _NUMERIC_STEP.match(text.strip())
    if not m:
        return None
    return m.group(1), m.group(2).strip()


def render_prose_steps_html(esc: Callable[[str], str], items: list[tuple[str, str]]) -> str:
    blocks = "".join(
        f'<div class="step-item step-item--prose">'
        f'<span class="step-num">{esc(num)}.</span>'
        f'<p class="step-prose">{esc(text)}</p></div>'
        for num, text in items
    )
    return f'<div class="step-list step-list--prose">{blocks}</div>'


def split_numeric_steps(lines: list[TextLine]) -> tuple[list[TextLine], list[tuple[str, str]], list[TextLine]] | None:
    """PDF: '1. …' '2. …' en líneas separadas (p.54 regla tres pasos)."""
    starts = [i for i, ln in enumerate(lines) if is_numeric_step_line(ln.text)]
    if len(starts) < 2:
        return None
    intro = lines[: starts[0]]
    items: list[tuple[str, str]] = []
    peeled: list[TextLine] = []
    for j, si in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(lines)
        chunk = lines[si:end]
        parsed = parse_numeric_step(chunk[0].text)
        if not parsed:
            return None
        num, first = parsed
        body = chunk[1:]
        if j + 1 >= len(starts) and body:
            cut = len(body)
            while cut > 0 and body[cut - 1].italic:
                cut -= 1
            peeled.extend(body[cut:])
            body = body[:cut]
        parts = [first] if first else []
        parts.extend(ln.text.strip() for ln in body if ln.text.strip())
        items.append((num, " ".join(parts)))
    return intro, items, peeled


def render_numeric_steps_page(
    esc: Callable[[str], str],
    collapse_spaced_fn: Callable[[str], str],
    intro: list[TextLine],
    items: list[tuple[str, str]],
    tail: list[TextLine],
    is_section_label: Callable[[TextLine], bool],
    group_prose_plain: Callable[[list[TextLine]], list[str]],
) -> list[str]:
    parts: list[str] = []
    label: TextLine | None = None
    prose_intro = intro
    if intro and is_section_label(intro[-1]):
        label = intro[-1]
        prose_intro = intro[:-1]
    parts.extend(group_prose_plain(prose_intro))
    if label is not None:
        parts.append(f'<p class="section-label">{esc(collapse_spaced_fn(label.text))}</p>')
    parts.append(render_prose_steps_html(esc, items))
    parts.extend(group_prose_plain(tail))
    return parts
