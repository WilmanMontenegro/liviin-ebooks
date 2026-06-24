"""Bloques HTML compartidos entre builds PDF → ebook."""
from __future__ import annotations

import re
from typing import Callable, Protocol

from pdf_text import collapse_spaced, fmt_prose_step

_NUMERIC_STEP = re.compile(r"^(\d+)\.\s*(.*)")


class TextLine(Protocol):
    text: str
    size: float
    italic: bool
    x: float


# PDF: citas con barra lateral empiezan ~x≥73; cuerpo y leads van ~x55
PULL_QUOTE_X_MIN = 70


def is_pull_quote_group(g: list[TextLine]) -> bool:
    if not g or not all(x.italic for x in g):
        return False
    text = " ".join(x.text for x in g).strip()
    if text.startswith("— MARÍA") or text.startswith("Interiorista y Home"):
        return False
    if text.endswith(":"):
        return False
    if not all(ln.x >= PULL_QUOTE_X_MIN for ln in g):
        return False
    sizes = [x.size for x in g]
    if all(9 <= s <= 14.5 for s in sizes):
        return True
    if all(12.5 <= s <= 14.5 for s in sizes):
        return True
    if (
        len(g) <= 2
        and all(9 <= s <= 10.5 for s in sizes)
        and len(text) < 115
        and text.rstrip().endswith((".", "—", "…"))
    ):
        return True
    return False


def continues_pull_quote(prev: TextLine, ln: TextLine) -> bool:
    """Misma cita tras merge de PDF — no cortar aunque el salto en y sea grande."""
    if not (prev.italic and ln.italic):
        return False
    if prev.x < PULL_QUOTE_X_MIN or ln.x < PULL_QUOTE_X_MIN:
        return False
    return 9 <= prev.size <= 14.5 and 9 <= ln.size <= 14.5


def is_opening_lead(g: list[TextLine]) -> bool:
    """PDF p.4: «Otra vez.» itálica al margen + filete ancho debajo (no pull-quote)."""
    if len(g) != 1:
        return False
    ln = g[0]
    text = ln.text.strip()
    return (
        ln.italic
        and ln.x < PULL_QUOTE_X_MIN
        and 11.5 <= ln.size <= 13
        and len(text) <= 24
        and text.endswith((".", "—", "…"))
    )


def render_opening_lead(esc: Callable[[str], str], g: list[TextLine]) -> list[str]:
    text = esc(" ".join(x.text for x in g))
    return [f'<p class="opening-lead">{text}</p>', '<div class="rule rule--full"></div>']


def is_section_subtitle(ln: TextLine) -> bool:
    if not ln.italic:
        return False
    if 14 <= ln.size <= 16:
        return True
    # ponytail: Transformar «interiorista y home coach» bajo nombre ≈11pt
    return 9.5 <= ln.size <= 13 and bool(
        re.match(r"^interiorista y home coach", ln.text.strip(), re.I)
    )


def render_title_block(
    esc: Callable[[str], str],
    titles: list[TextLine],
    subtitle: TextLine | None,
) -> list[str]:
    t0 = titles[0]
    if t0.italic or t0.size >= 26:
        th = "<br>".join(esc(collapse_spaced(t.text)) for t in titles)
        return [f'<div class="h1-italic" style="font-size:38px;">{th}</div>']
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
        f'<span class="step-num">{esc(fmt_prose_step(num))}.</span>'
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


def is_firma_cierre_page(lines: list[TextLine]) -> bool:
    """Cierre editorial: cita centrada + Con amor / M T E / nombre."""
    if len(lines) < 4:
        return False
    joined = " ".join(ln.text for ln in lines)
    return (
        lines[0].text.strip().startswith('"')
        and "Con amor" in joined
        and any(re.sub(r"\s+", "", ln.text.upper()) == "MTE" for ln in lines)
    )


def render_firma_cierre_page(
    esc: Callable[[str], str],
    lines: list[TextLine],
    pdf_page_no: int,
    folio: int,
) -> str:
    quote: list[TextLine] = []
    tail: list[TextLine] = []
    for ln in lines:
        if ln.text.strip().startswith("Con amor"):
            tail = lines[len(quote) :]
            break
        quote.append(ln)
    quote_html = "<br>".join(esc(ln.text) for ln in quote)
    con_amor = esc(tail[0].text) if tail else "Con amor,"
    iniciales = esc(tail[1].text) if len(tail) > 1 else "M T E"
    nombre = esc(tail[2].text) if len(tail) > 2 else "María Teresa Espinosa"
    return f"""<!-- folio {folio} pdf p{pdf_page_no} -->
<div class="page page-crema">
  <div class="content cierre-final">
    <p class="frase-cierre">{quote_html}</p>
    <div class="firma firma--center">
      <p class="con-carino">{con_amor}</p>
      <p class="firma-iniciales">{iniciales}</p>
      <p class="firma-nombre">{nombre}</p>
    </div>
  </div>
</div>
"""
