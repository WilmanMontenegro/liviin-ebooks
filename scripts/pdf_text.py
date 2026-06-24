"""Texto desde PDF: letter-spacing y gaps entre palabras."""
from __future__ import annotations

import re
from collections.abc import Callable
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


def collapse_letter_spaced_segment(seg: str) -> str:
    """'E L' → 'EL'; 'LA REGLA' queda igual."""
    seg = seg.strip()
    if not seg:
        return seg
    if re.search(r"[a-záéíóúñ]", seg):
        return re.sub(r"\s+", " ", seg)
    tokens = seg.split()
    if tokens and all(len(re.sub(r"[^\wÁÉÍÓÚÑáéíóúñ]", "", t)) <= 2 for t in tokens):
        return "".join(tokens)
    return re.sub(r"\s+", " ", seg)


def collapse_from_raw_spacing(raw: str) -> str:
    """Usa dobles espacios del PDF como límites de palabra (labels numerados, tags)."""
    parts = [p.strip() for p in re.split(r"\s{2,}", raw.strip()) if p.strip()]
    words: list[str] = []
    for p in parts:
        if re.fullmatch(r"0\s*\d", p):
            words.append(re.sub(r"\s+", "", p))
        elif p in ("·", "•"):
            if words:
                words[-1] = f"{words[-1]} ·"
            else:
                words.append("·")
        else:
            words.append(collapse_letter_spaced_segment(p))
    return " ".join(words)


def _label_words(s: str) -> list[str]:
    title = s.split("·", 1)[1].strip() if "·" in s else s.strip()
    return [re.sub(r"[^\wÁÉÍÓÚÑ]", "", w) for w in title.split() if re.sub(r"[^\wÁÉÍÓÚÑ]", "", w)]


def _looks_collapsed_label(s: str) -> bool:
    words = _label_words(s)
    if not words:
        return False
    singles = sum(len(w) <= 2 for w in words)
    if singles >= max(3, len(words) // 2):
        return False
    return any(len(w) >= 4 for w in words)


def _raw_has_merged_words(raw_col: str, gap_col: str) -> bool:
    """True si raw pegó palabras que gap separa (DISEÑADORADEL vs DISEÑADORA DEL)."""
    if not _looks_collapsed_label(gap_col):
        return False
    rw, gw = _label_words(raw_col), _label_words(gap_col)
    if len(gw) <= len(rw):
        return False
    gap_blob = "".join(gw)
    for w in rw:
        if len(w) >= 10 and w not in gw and w in gap_blob:
            return True
    return False


def extract_line_text(raw: str, chars: list[dict]) -> str:
    """Texto de línea PDF: letter-spacing vía gaps o dobles espacios."""
    raw = raw.strip()
    if not raw:
        return raw
    if needs_gap_extract(raw):
        if chars and re.search(r"\s{2,}", raw):
            gap_raw = chars_to_line_text(chars)
            if re.search(r"\s{2,}", gap_raw):
                raw_col = collapse_from_raw_spacing(raw)
                gap_col = collapse_from_raw_spacing(gap_raw)
                if _raw_has_merged_words(raw_col, gap_col):
                    return gap_col
            return collapse_from_raw_spacing(raw)
        return collapse_spaced(chars_to_line_text(chars)) if chars else collapse_spaced(raw)
    return raw


def _span_raw_text(sp: dict) -> str:
    chars = sp.get("chars") or []
    if chars:
        return "".join(c["c"] for c in chars)
    return sp.get("text", "")


def _span_style(sp: dict) -> tuple[bool, bool]:
    return bool(sp["flags"] & 16), bool(sp["flags"] & 2)


def spans_need_inline_html(spans: list[dict]) -> bool:
    """True si la línea mezcla texto plano con énfasis (itálica/negrita) entre spans."""
    styled: list[tuple[bool, bool]] = []
    plain = 0
    for sp in spans:
        if not _span_raw_text(sp).strip():
            continue
        bold, italic = _span_style(sp)
        if bold or italic:
            styled.append((bold, italic))
        else:
            plain += 1
    if plain and styled:
        return True
    return len(set(styled)) > 1


def render_spans_inline_html(spans: list[dict], esc: Callable[[str], str]) -> str:
    """Énfasis inline del PDF → <em>/<strong> dentro de .body."""
    parts: list[str] = []
    for sp in spans:
        raw = _span_raw_text(sp)
        if not raw:
            continue
        bold, italic = _span_style(sp)
        if bold or italic:
            inner = esc(raw)
            if bold and italic:
                chunk = f"<strong><em>{inner}</em></strong>"
            elif bold:
                chunk = f"<strong>{inner}</strong>"
            else:
                chunk = f"<em>{inner}</em>"
        else:
            chunk = esc(raw)
        parts.append(chunk)
    return "".join(parts)


def collapse_orphan_caps(text: str) -> str:
    """Palabra suelta letter-spaced: 'S A L E' / 'I N  M  E  D  I A  T A' → 'SALE' / 'INMEDIATA'."""
    text = text.strip()
    if re.search(r"\s{2,}", text):
        parts = [collapse_letter_spaced_segment(p) for p in re.split(r"\s{2,}", text) if p.strip()]
        return "".join(parts)
    tokens = text.split()
    if tokens and all(len(t) <= 2 for t in tokens):
        return "".join(tokens)
    return text


def _is_letter_spaced_token(token: str) -> bool:
    core = re.sub(r"[^\wÁÉÍÓÚÑáéíóúñ]", "", token)
    return len(core) <= 1


def normalize_title_caps(s: str) -> str:
    """Mezcla palabras normales + tramos letter-spaced: 'MUY P E Q U E Ñ A.' → 'MUY PEQUEÑA.'"""
    s = re.sub(r"\s+", " ", s.strip())
    if re.search(r"\s{2,}", s):
        return collapse_from_raw_spacing(s)
    tokens = s.split()
    out: list[str] = []
    run: list[str] = []
    for t in tokens:
        if _is_letter_spaced_token(t):
            run.append(t)
        else:
            if run:
                out.append("".join(run))
                run = []
            out.append(t)
    if run:
        out.append("".join(run))
    return " ".join(out)


def normalize_label_part(s: str) -> str:
    s = s.strip()
    if re.fullmatch(r"0\s*\d", s):
        return re.sub(r"\s+", "", s)
    if re.search(r"\s{2,}", s):
        return collapse_from_raw_spacing(s)
    tokens = s.split()
    if tokens and any(_is_letter_spaced_token(t) for t in tokens):
        return normalize_title_caps(s)
    return re.sub(r"\s+", " ", s)


def merge_orphan_caps_lines(lines: list, is_numbered_label_fn) -> list:
    """Une continuaciones en caps bajo la etiqueta numerada (SALE, INMEDIATA…)."""
    if not lines:
        return lines
    out = [lines[0]]
    for ln in lines[1:]:
        prev = out[-1]
        if is_numbered_label_fn(prev.text) and is_orphan_caps_line(
            ln.text, ln.size, is_numbered_label_fn
        ):
            merged = f"{prev.text.rstrip()} {collapse_orphan_caps(ln.text)}"
            out[-1] = type(prev)(**{**prev.__dict__, "text": merged})
        else:
            out.append(ln)
    return out


def is_orphan_caps_line(text: str, size: float, is_numbered_label_fn) -> bool:
    """Línea suelta en caps tras un 01· (SALE, I N M E D I A T A…) — no es cuerpo."""
    t = text.strip()
    if not t or size > 10.5 or is_numbered_label_fn(t):
        return False
    if re.search(r"[a-záéíóúñ]", t):
        return False
    if len(collapse_orphan_caps(t)) > 24:
        return False
    tokens = t.split()
    if len(tokens) == 1:
        return True
    return all(len(tok) <= 2 for tok in tokens)


def absorb_numbered_orphans(label: str, desc: list, is_numbered_label_fn) -> tuple[str, list]:
    """Si el PDF partió el título, la cola no debe ir al párrafo."""
    while desc and is_orphan_caps_line(desc[0].text, desc[0].size, is_numbered_label_fn):
        label = f"{label.rstrip()} {collapse_orphan_caps(desc[0].text)}"
        desc = desc[1:]
    return label, desc


def _digits(s: str | int) -> int:
    if isinstance(s, int):
        return s
    d = re.sub(r"\D", "", collapse_spaced(str(s)))
    return int(d) if d else 0


def fmt_structural(n: str | int) -> str:
    """Bloques editoriales: 01 · LABEL, step-list, índice, descubrimientos."""
    return f"{_digits(n):02d}"


def fmt_inventory(n: str | int) -> str:
    """Mapas e inventarios largos: 1, 2, 13…"""
    return str(_digits(n))


def fmt_prose_step(n: str | int) -> str:
    """Pasos en prosa narrativa: 1. 2. 3. (sin cero)."""
    return fmt_inventory(n)


def numbered_caps_html(num: str, title: str) -> str:
    """Label caps PDF: una sola línea sans como '04 · COMUNICACIÓN Y FEEDBACK'."""
    n, t = normalize_label_part(num), normalize_label_part(title)
    if n:
        return f"{html_escape(fmt_structural(n))} · {html_escape(t)}"
    return html_escape(t)


if __name__ == "__main__":
    assert collapse_spaced("0 1  ·  L I M P I E Z A  P R O F U N D A") == "01 · LIMPIEZA PROFUNDA"
    assert collapse_spaced("0 1  ·  D I S E Ñ A D O R A  D E L  S I S T E M A") == "01 · DISEÑADORA DEL SISTEMA"
    assert (
        collapse_from_raw_spacing("0 1  ·  E L  C I E R R E  D E L  D Í A")
        == "01 · EL CIERRE DEL DÍA"
    )
    assert (
        collapse_from_raw_spacing("0 4  ·  C O M P R A R  ( C O N  A S E R T I V I D A D )")
        == "04 · COMPRAR (CON ASERTIVIDAD)"
    )
    assert collapse_orphan_caps("I N  M  E  D  I A  T A") == "INMEDIATA"
    assert normalize_title_caps("MUY P E Q U E Ñ A.") == "MUY PEQUEÑA."
    assert is_orphan_caps_line("SALE", 9.0, lambda t: False)
    assert is_orphan_caps_line("I N  M  E  D  I A  T A", 9.0, lambda t: False)
    assert not is_orphan_caps_line("Cada vez que algo", 11.0, lambda t: False)
    assert absorb_numbered_orphans("02 · LA REGLA DE UNO ENTRA, UNO", [type("L", (), {"text": "SALE", "size": 9})()], lambda t: t.startswith("02"))[0].endswith("SALE")
    assert numbered_caps_html("01", "EL MINUTO DE LA ACCIÓN INMEDIATA") == "01 · EL MINUTO DE LA ACCIÓN INMEDIATA"
    assert _raw_has_merged_words("01 · DISEÑADORADEL SISTEMA", "01 · DISEÑADORA DEL SISTEMA")
    assert _raw_has_merged_words("01 · LARENUNCIA", "01 · LA RENUNCIA")
    assert not _raw_has_merged_words("04 · COMPRAR (CON ASERTIVIDAD)", "04 · COMPRAR (CON ASERTIVIDAD)")
    assert fmt_structural("0 1") == "01"
    assert fmt_inventory(13) == "13"
    assert fmt_prose_step("2") == "2"
