#!/usr/bin/env python3
"""Mesa: tips → section-label+pull-quote; círculos → body-list; 2col → bank-grid dual ol."""
from __future__ import annotations

import re
from pathlib import Path

MESA = Path(__file__).resolve().parents[1] / "web" / "mesa.html"


def revert_guia_tips(text: str) -> str:
    def block(m: re.Match[str]) -> str:
        label = m.group(1)
        body = m.group(2).strip()
        if label:
            return (
                f'    <p class="section-label">{label}</p>\n'
                f'    <div class="pull-quote"><p>{body}</p></div>'
            )
        return f'    <div class="pull-quote"><p>{body}</p></div>'

    pat = re.compile(
        r'<div class="caja-crema guia-tip">\s*'
        r'(?:<p class="section-label">([^<]*)</p>\s*)?'
        r'<p class="reminder-text">(.*?)</p>\s*</div>',
        re.DOTALL,
    )
    return pat.sub(block, text)


def circles_to_body_list(text: str) -> str:
    pat = re.compile(
        r'<ol class="numbered-circles[^"]*">(.*?)</ol>',
        re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        return f'<ul class="body-list">{inner}</ul>'

    return pat.sub(repl, text)


def split_two_col_lists(text: str) -> str:
    pat = re.compile(
        r'<ol class="numbered numbered--2col[^"]*">(.*?)</ol>',
        re.DOTALL,
    )

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        items = re.findall(r"<li[^>]*>.*?</li>", inner, re.DOTALL)
        if len(items) < 2:
            return m.group(0)
        mid = (len(items) + 1) // 2
        a, b = items[:mid], items[mid:]
        start = mid + 1
        col_b = (
            f'      <ol class="numbered numbered--bank numbered--continue" '
            f'style="--list-start:{mid}">\n        '
            + "\n        ".join(b)
            + "\n      </ol>"
        )
        return (
            "    <div class=\"bank-grid\">\n"
            "      <ol class=\"numbered numbered--bank\">\n        "
            + "\n        ".join(a)
            + "\n      </ol>\n"
            + col_b
            + "\n    </div>"
        )

    return pat.sub(repl, text)


def main() -> None:
    text = MESA.read_text(encoding="utf-8")
    n_tip = len(re.findall(r"caja-crema guia-tip", text))
    text = revert_guia_tips(text)
    text = circles_to_body_list(text)
    text = split_two_col_lists(text)
    MESA.write_text(text, encoding="utf-8")
    print(f"OK mesa.html — guia-tip revertidos: {n_tip}")
    print(f"  numbered-circles restantes: {text.count('numbered-circles')}")
    print(f"  numbered--2col restantes: {text.count('numbered--2col')}")


if __name__ == "__main__":
    main()
