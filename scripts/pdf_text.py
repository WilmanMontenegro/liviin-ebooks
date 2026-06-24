"""Texto desde PDF: letter-spacing y gaps entre palabras."""
from __future__ import annotations

import re
from html import escape as html_escape

_GAP_MIN = 9.6
_GAP_RATIO = 1.35


def needs_gap_extract(text: str) -> bool:
    """True solo para líneas PDF con letter-spacing (labels, tags, bandas)."""
    t = text.strip()
    if re.match(r"^0\s*\d\s*·", t):
        return True
    if re.search(r"[a-záéíóúñ]", t):
        return False
    return bool(re.search(r"(?:[A-ZÁÉÍÓÚÑ]\s){3,}", t))


def _gap_width(chars: list[dict], space_i: int) -> float | None:
    j = space_i + 1
    while j < len(chars) and chars[j]["c"] == " ":
        j += 1
    k = space_i - 1
    while k >= 0 and chars[k]["c"] == " ":
        k -= 1
    if k < 0 or j >= len(chars):
        return None
    return chars[j]["origin"][0] - chars[k]["origin"][0]


def _word_break_before(chars: list[dict], char_i: int) -> bool:
    """True si char_i empieza palabra nueva (tras espacio doble o gap ancho)."""
    if char_i <= 0 or chars[char_i]["c"] == " ":
        return False
    j = char_i - 1
    while j >= 0 and chars[j]["c"] == " ":
        j -= 1
    if j < 0:
        return False
    prev = chars[j]["c"]
    cur = chars[char_i]["c"]
    if prev.isdigit() and cur == "·":
        return False

    space_run = char_i - 1 - j
    if space_run >= 2:
        return True
    if space_run < 1:
        return False

    gaps: list[float] = []
    for i in range(1, len(chars)):
        if chars[i]["c"] != " " or chars[i - 1]["c"] == " ":
            continue
        w = _gap_width(chars, i)
        if w is not None:
            gaps.append(w)
    inner = [g for g in gaps if g < 9.5]
    med = sorted(inner)[len(inner) // 2] if inner else 7.0
    w = _gap_width(chars, char_i - 1)
    return w is not None and w >= _GAP_MIN and w > med * _GAP_RATIO


def chars_to_line_text(chars: list[dict]) -> str:
    """Une chars; límites de palabra → doble espacio para collapse_spaced."""
    if not chars:
        return ""
    segments: list[list[tuple[str, bool]]] = []
    seg: list[tuple[str, bool]] = []
    for i, ch in enumerate(chars):
        c = ch["c"]
        if c == " ":
            continue
        spaced = i > 0 and chars[i - 1]["c"] == " "
        if seg and _word_break_before(chars, i):
            segments.append(seg)
            seg = []
        seg.append((c, spaced))
    if seg:
        segments.append(seg)

    parts: list[str] = []
    for seg in segments:
        if len(seg) >= 2 and all(sp for _, sp in seg[1:]):
            parts.append(" ".join(c for c, _ in seg))
        else:
            parts.append("".join(c for c, _ in seg))
    return "  ".join(parts)


def collapse_spaced(s: str) -> str:
    """PDF caps con letter-spacing: 'E L  C A M B I O' → 'EL CAMBIO'; '0 1' → '01'."""
    s = s.strip()
    if re.fullmatch(r"0\s*\d", s):
        return re.sub(r"\s+", "", s)
    if not re.search(r"(?:\S\s){3,}", s):
        return s
    return " ".join(re.sub(r"\s+", "", c) for c in re.split(r"\s{2,}", s) if c.strip())


_DIGIT_RE = re.compile(r"\d+")


def title_digits_html(text: str) -> str:
    """Dígitos en títulos display: más pequeños, baseline (PDF Liberation Serif oldstyle)."""
    t = collapse_spaced(text)
    out: list[str] = []
    pos = 0
    for m in _DIGIT_RE.finditer(t):
        if m.start() > pos:
            out.append(html_escape(t[pos : m.start()]))
        out.append(f'<span class="title-digit">{html_escape(m.group())}</span>')
        pos = m.end()
    out.append(html_escape(t[pos:]))
    return "".join(out)


if __name__ == "__main__":
    assert collapse_spaced("0 1  ·  L I M P I E Z A  P R O F U N D A") == "01 · LIMPIEZA PROFUNDA"
    assert collapse_spaced("0 1  ·  D I S E Ñ A D O R A  D E L  S I S T E M A") == "01 · DISEÑADORA DEL SISTEMA"
    assert title_digits_html("LOS 4 ACUERDOS") == 'LOS <span class="title-digit">4</span> ACUERDOS'
