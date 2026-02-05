"""Formatting and drawing utility helpers."""

from __future__ import annotations

from typing import Any, List, Protocol

from dateutil import parser as dateutil_parser


class TextWidthProvider(Protocol):
    def text_width(self, text: str, size: int, bold: bool = False) -> float:
        ...


class PdfPathCanvas(Protocol):
    k: float
    h: float

    def rect(self, x: float, y: float, width: float, height: float, style: str) -> None:
        ...

    def _out(self, value: str) -> None:
        ...


def fmt_money(amount: float, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def fmt_qty(qty: Any) -> str:
    try:
        quantity = float(qty)
        if quantity.is_integer():
            return str(int(quantity))
        return str(quantity)
    except Exception:
        return str(qty)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def fmt_date(raw: str) -> str:
    """Parse a date string and return it formatted as 'Mar 14, 2025'."""
    raw = raw.strip()
    if not raw:
        return raw
    try:
        dt = dateutil_parser.parse(raw)
        return dt.strftime("%b %d, %Y")
    except (ValueError, OverflowError):
        return raw


def split_lines(text: str) -> List[str]:
    if not text:
        return []
    return [line for line in text.split("\n") if line.strip() != ""]


def wrap_text(
    fonts_obj: TextWidthProvider,
    text: str,
    max_width: float,
    font_size: int,
    bold: bool = False,
) -> List[str]:
    def line_width(value: str) -> float:
        return fonts_obj.text_width(value, font_size, bold=bold)

    def wrap_paragraph(paragraph: str) -> List[str]:
        words = paragraph.split()
        if not words:
            return [paragraph]

        lines: List[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if line_width(candidate) <= max_width:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = word
                continue

            chunk = ""
            for char in word:
                candidate_chunk = chunk + char
                if chunk and line_width(candidate_chunk) > max_width:
                    lines.append(chunk)
                    chunk = char
                else:
                    chunk = candidate_chunk
            current = chunk

        if current:
            lines.append(current)
        return lines

    result: List[str] = []
    for paragraph in text.split("\n"):
        result.extend(wrap_paragraph(paragraph))
    return result if result else [text]


def round_rect(
    pdf: PdfPathCanvas,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    fill: bool = True,
) -> None:
    radius = max(0.0, min(radius, width / 2.0, height / 2.0))
    if radius == 0:
        pdf.rect(x, y, width, height, "F" if fill else "S")
        return

    k = pdf.k
    hp = pdf.h
    kappa = 0.5522847498307936  # circle approximation constant

    def arc(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        pdf._out(
            "%.2f %.2f %.2f %.2f %.2f %.2f c"
            % (x1 * k, (hp - y1) * k, x2 * k, (hp - y2) * k, x3 * k, (hp - y3) * k)
        )

    pdf._out("%.2f %.2f m" % ((x + radius) * k, (hp - y) * k))
    pdf._out("%.2f %.2f l" % ((x + width - radius) * k, (hp - y) * k))
    arc(
        x + width - radius + radius * kappa,
        y,
        x + width,
        y + radius - radius * kappa,
        x + width,
        y + radius,
    )
    pdf._out("%.2f %.2f l" % ((x + width) * k, (hp - (y + height - radius)) * k))
    arc(
        x + width,
        y + height - radius + radius * kappa,
        x + width - radius + radius * kappa,
        y + height,
        x + width - radius,
        y + height,
    )
    pdf._out("%.2f %.2f l" % ((x + radius) * k, (hp - (y + height)) * k))
    arc(
        x + radius - radius * kappa,
        y + height,
        x,
        y + height - radius + radius * kappa,
        x,
        y + height - radius,
    )
    pdf._out("%.2f %.2f l" % (x * k, (hp - (y + radius)) * k))
    arc(x, y + radius - radius * kappa, x + radius - radius * kappa, y, x + radius, y)

    pdf._out("f" if fill else "S")
