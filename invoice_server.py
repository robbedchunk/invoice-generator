import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF  # type: ignore
import fpdf as fpdf_module  # for cache mode

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Avoid writing font cache files into system font directories
fpdf_module.FPDF_CACHE_MODE = 1

PAGE_W = 612
PAGE_H = 792

# Layout constants (points, top-left origin)
X_LEFT = 48
X_ITEM = 45
X_BAR = 30
BAR_W = 552
BAR_H = 20

# First-page table header
BAR_Y_FIRST = 209.0
BAR_TEXT_Y_FIRST = 221.2

# Continuation-page table header (no top invoice header)
BAR_Y_CONT = 12.8
BAR_TEXT_Y_CONT = 24.8

TITLE_RIGHT = 573
NUMBER_RIGHT = 568
DATE_LABEL_RIGHT = 461
RIGHT_AMOUNT = 566
RATE_RIGHT = 492
LABEL_RIGHT = 491

NAME_Y = 33.8
TITLE_Y = 48.0
NUMBER_Y = 67.5
DATE_Y = 117.8
BALANCE_Y = 141.8

BILL_TO_LABEL_Y = 131.2
BILL_TO_NAME_Y = 147.0
BILL_TO_ADDR_Y = 159.0
ADDR_LINE_H = 12.0

BALANCE_BOX_X = 317.0
BALANCE_BOX_Y = 126.0
BALANCE_BOX_W = 270.0
BALANCE_BOX_H = 27.0

ITEMS_START_Y_FIRST = 246.8
ITEMS_START_Y_CONT = 42.0
ITEM_ROW_H = 17.2

TOTALS_START_Y_FIRST = 315.8
TOTAL_ROW_H_FIRST = 17.2
TOTALS_START_Y_CONT = 141.8
TOTAL_ROW_H_CONT = 21.7

NOTES_LABEL_Y_FIRST = 401.2
NOTES_TEXT_Y_FIRST = 418.5
NOTES_LINE_H_FIRST = 17.2
NOTES_LABEL_Y_CONT = 240.0
NOTES_TEXT_Y_CONT = 256.5
NOTES_LINE_H_CONT = 17.2

# Pagination capacities (empirically derived from existing invoices)
FIRST_PAGE_CAPACITY = 28
MID_PAGE_CAPACITY = 40
LAST_PAGE_CAPACITY = 6

# Colors (RGB)
COLOR_TITLE = (94, 94, 94)          # #5E5E5E
COLOR_INVOICE_NUM = (149, 149, 149) # #959595
COLOR_LABEL = (105, 105, 105)       # #696969
COLOR_BILLTO = (145, 145, 145)      # #919191
COLOR_TEXT = (106, 106, 106)        # #6A6A6A
COLOR_TEXT_ALT = (115, 115, 115)    # #737373
COLOR_ITEM = (105, 105, 105)        # #696969
COLOR_NUM = (113, 113, 113)         # #717171
COLOR_NOTES = (111, 111, 111)       # #6F6F6F
COLOR_BAR = (58, 58, 58)            # #3A3A3A
COLOR_BAR_TEXT = (234, 234, 234)    # #EAEAEA
COLOR_BOX = (249, 249, 249)         # #F9F9F9

FONT_SIZE_TITLE = 28
FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 9

BAR_RADIUS = 4.0
BOX_RADIUS = 4.0

DEFAULT_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "\u20ac",
    "GBP": "\u00a3",
}


def _find_font_path(env_var: str, candidates: List[str]) -> Optional[str]:
    # Allow override via env var
    override = os.getenv(env_var)
    if override and os.path.exists(override):
        return override

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class FontManager:
    def __init__(self, pdf: FPDF) -> None:
        self.pdf = pdf
        self.family = "Helvetica"
        self.use_unicode = False
        self.has_bold = False
        self.font_path = _find_font_path(
            "INVOICE_FONT_PATH",
            [
                # macOS
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Apple Symbols.ttf",
                # Linux (common distro paths)
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/gnu-free/FreeSans.ttf",
                # Bundled fallback (always available)
                os.path.join(_SCRIPT_DIR, "fonts", "DejaVuSans.ttf"),
            ],
        )
        self.font_bold_path = _find_font_path(
            "INVOICE_FONT_BOLD_PATH",
            [
                # Linux bold variants
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/gnu-free/FreeSansBold.ttf",
                # Bundled fallback (always available)
                os.path.join(_SCRIPT_DIR, "fonts", "DejaVuSans-Bold.ttf"),
            ],
        )
        if self.font_path:
            try:
                self.pdf.add_font("InvoiceFont", "", self.font_path, uni=True)
                if self.font_bold_path:
                    self.pdf.add_font("InvoiceFont", "B", self.font_bold_path, uni=True)
                    self.has_bold = True
                self.family = "InvoiceFont"
                self.use_unicode = True
            except Exception:
                self.family = "Helvetica"
                self.use_unicode = False

    def set_font(self, size: int) -> None:
        self.pdf.set_font(self.family, "", size)

    def text_width(self, text: str, size: int) -> float:
        self.set_font(size)
        return self.pdf.get_string_width(text)

    def draw_text(self, x: float, y: float, text: str, size: int, color: Tuple[int, int, int], bold: bool = False) -> None:
        self.set_font(size)
        self.pdf.set_text_color(*color)
        if bold and self.has_bold:
            self.pdf.set_font(self.family, "B", size)
            self.pdf.text(x, y, text)
        elif bold:
            self.pdf.text(x, y, text)
            self.pdf.text(x + 0.4, y, text)
        else:
            self.pdf.text(x, y, text)


def _fmt_money(amount: float, symbol: str) -> str:
    return f"{symbol}{amount:,.2f}"


def _fmt_qty(qty: Any) -> str:
    try:
        q = float(qty)
        if q.is_integer():
            return str(int(q))
        return str(q)
    except Exception:
        return str(qty)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _split_lines(text: str) -> List[str]:
    if not text:
        return []
    return [line for line in text.split("\n") if line.strip() != ""]

def _round_rect(pdf: FPDF, x: float, y: float, w: float, h: float, r: float, fill: bool = True) -> None:
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    if r == 0:
        pdf.rect(x, y, w, h, "F" if fill else "S")
        return

    k = pdf.k
    hp = pdf.h
    c = 0.5522847498307936  # kappa for circle approximation

    def _arc(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        pdf._out(
            "%.2f %.2f %.2f %.2f %.2f %.2f c"
            % (x1 * k, (hp - y1) * k, x2 * k, (hp - y2) * k, x3 * k, (hp - y3) * k)
        )

    pdf._out("%.2f %.2f m" % ((x + r) * k, (hp - y) * k))
    pdf._out("%.2f %.2f l" % ((x + w - r) * k, (hp - y) * k))
    _arc(x + w - r + r * c, y, x + w, y + r - r * c, x + w, y + r)
    pdf._out("%.2f %.2f l" % ((x + w) * k, (hp - (y + h - r)) * k))
    _arc(x + w, y + h - r + r * c, x + w - r + r * c, y + h, x + w - r, y + h)
    pdf._out("%.2f %.2f l" % ((x + r) * k, (hp - (y + h)) * k))
    _arc(x + r - r * c, y + h, x, y + h - r + r * c, x, y + h - r)
    pdf._out("%.2f %.2f l" % (x * k, (hp - (y + r)) * k))
    _arc(x, y + r - r * c, x + r - r * c, y, x + r, y)

    pdf._out("f" if fill else "S")


def render_invoice(data: Dict[str, Any]) -> bytes:
    pdf = FPDF(unit="pt", format="letter")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    fonts = FontManager(pdf)

    # Currency + totals
    currency = str(data.get("currency", "USD")).upper()
    symbol = DEFAULT_CURRENCY_SYMBOLS.get(currency, "$" if currency == "USD" else f"{currency} ")

    items = data.get("items", []) or []
    subtotal = 0.0
    for item in items:
        qty = _safe_float(item.get("quantity", 1), 1.0)
        unit_cost = _safe_float(item.get("unit_cost", 0.0), 0.0)
        subtotal += qty * unit_cost

    discounts = data.get("discounts", 0)
    discount_value = 0.0
    discount_label = None
    if discounts:
        try:
            discount_value = float(discounts)
        except Exception:
            discount_value = 0.0

        fields = data.get("fields", {}) or {}
        if fields.get("discounts") == "%":
            discount_value = subtotal * (discount_value / 100.0)
            d_display = int(discounts) if float(discounts).is_integer() else discounts
            discount_label = f"Discount ({d_display}%):"
        else:
            discount_label = "Discount:"

    total = subtotal - discount_value

    qty_center = 375
    rate_center = 457
    amount_center = 531

    def draw_table_header(bar_y: float, text_y: float) -> None:
        pdf.set_fill_color(*COLOR_BAR)
        _round_rect(pdf, X_BAR, bar_y, BAR_W, BAR_H, BAR_RADIUS, fill=True)

        fonts.draw_text(X_ITEM, text_y, "Item", FONT_SIZE_SMALL, COLOR_BAR_TEXT, bold=True)
        qty_label = "Quantity"
        rate_label = "Rate"
        amt_label = "Amount"

        fonts.draw_text(qty_center - fonts.text_width(qty_label, FONT_SIZE_SMALL) / 2.0, text_y, qty_label, FONT_SIZE_SMALL, COLOR_BAR_TEXT, bold=True)
        fonts.draw_text(rate_center - fonts.text_width(rate_label, FONT_SIZE_SMALL) / 2.0, text_y, rate_label, FONT_SIZE_SMALL, COLOR_BAR_TEXT, bold=True)
        fonts.draw_text(amount_center - fonts.text_width(amt_label, FONT_SIZE_SMALL) / 2.0, text_y, amt_label, FONT_SIZE_SMALL, COLOR_BAR_TEXT, bold=True)

    def draw_items(start_y: float, page_items: List[Dict[str, Any]], row_h: float) -> None:
        y = start_y
        for item in page_items:
            name = str(item.get("name", "")).strip()
            qty = _safe_float(item.get("quantity", 1), 1.0)
            unit_cost = _safe_float(item.get("unit_cost", 0.0), 0.0)
            amount = qty * unit_cost

            if name:
                fonts.draw_text(X_ITEM, y, name, FONT_SIZE_NORMAL, COLOR_ITEM, bold=True)

            qty_text = _fmt_qty(qty)
            rate_text = _fmt_money(unit_cost, symbol)
            amt_text = _fmt_money(amount, symbol)

            fonts.draw_text(qty_center - fonts.text_width(qty_text, FONT_SIZE_NORMAL) / 2.0, y, qty_text, FONT_SIZE_NORMAL, COLOR_NUM, bold=False)
            fonts.draw_text(RATE_RIGHT - fonts.text_width(rate_text, FONT_SIZE_NORMAL), y, rate_text, FONT_SIZE_NORMAL, COLOR_NUM, bold=False)
            fonts.draw_text(RIGHT_AMOUNT - fonts.text_width(amt_text, FONT_SIZE_NORMAL), y, amt_text, FONT_SIZE_NORMAL, COLOR_NUM, bold=False)

            y += row_h

    def draw_totals(start_y: float, row_h: float) -> None:
        totals_y = start_y
        fonts.draw_text(LABEL_RIGHT - fonts.text_width("Subtotal:", FONT_SIZE_NORMAL), totals_y, "Subtotal:", FONT_SIZE_NORMAL, (118, 118, 118), bold=False)
        fonts.draw_text(RIGHT_AMOUNT - fonts.text_width(_fmt_money(subtotal, symbol), FONT_SIZE_NORMAL), totals_y, _fmt_money(subtotal, symbol), FONT_SIZE_NORMAL, COLOR_NUM, bold=False)

        totals_y += row_h
        if discount_label:
            fonts.draw_text(LABEL_RIGHT - fonts.text_width(discount_label, FONT_SIZE_NORMAL), totals_y, discount_label, FONT_SIZE_NORMAL, (118, 118, 118), bold=False)
            fonts.draw_text(RIGHT_AMOUNT - fonts.text_width(_fmt_money(discount_value, symbol), FONT_SIZE_NORMAL), totals_y, _fmt_money(discount_value, symbol), FONT_SIZE_NORMAL, COLOR_NUM, bold=False)
            totals_y += row_h

        fonts.draw_text(LABEL_RIGHT - fonts.text_width("Total:", FONT_SIZE_NORMAL), totals_y, "Total:", FONT_SIZE_NORMAL, (118, 118, 118), bold=False)
        fonts.draw_text(RIGHT_AMOUNT - fonts.text_width(_fmt_money(total, symbol), FONT_SIZE_NORMAL), totals_y, _fmt_money(total, symbol), FONT_SIZE_NORMAL, COLOR_NUM, bold=False)

    def draw_notes(label_y: float, text_y: float, line_h: float) -> None:
        notes = str(data.get("notes", "")).strip()
        if not notes:
            return
        fonts.draw_text(X_ITEM, label_y, "Notes:", FONT_SIZE_NORMAL, COLOR_TEXT, bold=False)
        note_lines = _split_lines(notes)
        for idx, line in enumerate(note_lines):
            fonts.draw_text(X_ITEM, text_y + (idx * line_h), line, FONT_SIZE_NORMAL, COLOR_NOTES, bold=False)

    def draw_header_full() -> None:
        sender = str(data.get("from", "")).strip()
        if sender:
            fonts.draw_text(X_LEFT, NAME_Y, sender, FONT_SIZE_NORMAL, COLOR_TEXT, bold=True)

        fonts.draw_text(
            TITLE_RIGHT - fonts.text_width("INVOICE", FONT_SIZE_TITLE),
            TITLE_Y,
            "INVOICE",
            FONT_SIZE_TITLE,
            COLOR_TITLE,
            bold=False,
        )

        number = str(data.get("number", "")).strip()
        if number:
            inv_line = f"# {number}"
            fonts.draw_text(
                NUMBER_RIGHT - fonts.text_width(inv_line, FONT_SIZE_NORMAL),
                NUMBER_Y,
                inv_line,
                FONT_SIZE_NORMAL,
                COLOR_INVOICE_NUM,
                bold=False,
            )

        to_block = _split_lines(str(data.get("to", "")).strip())
        if to_block:
            fonts.draw_text(X_LEFT, BILL_TO_LABEL_Y, "Bill To:", FONT_SIZE_SMALL, COLOR_BILLTO, bold=False)
            if len(to_block) > 0:
                fonts.draw_text(X_LEFT, BILL_TO_NAME_Y, to_block[0], FONT_SIZE_NORMAL, COLOR_TEXT, bold=True)
            if len(to_block) > 1:
                fonts.draw_text(X_LEFT, BILL_TO_ADDR_Y, to_block[1], FONT_SIZE_SMALL, COLOR_TEXT_ALT, bold=False)
            if len(to_block) > 2:
                fonts.draw_text(X_LEFT, BILL_TO_ADDR_Y + ADDR_LINE_H, to_block[2], FONT_SIZE_SMALL, COLOR_TEXT_ALT, bold=False)
            if len(to_block) > 3:
                for i, line in enumerate(to_block[3:], start=2):
                    fonts.draw_text(X_LEFT, BILL_TO_ADDR_Y + ADDR_LINE_H * (i + 1), line, FONT_SIZE_SMALL, COLOR_TEXT_ALT, bold=False)

        date_str = str(data.get("date", "")).strip()
        if date_str:
            fonts.draw_text(
                DATE_LABEL_RIGHT - fonts.text_width("Date:", FONT_SIZE_NORMAL),
                DATE_Y,
                "Date:",
                FONT_SIZE_NORMAL,
                COLOR_LABEL,
                bold=False,
            )
            fonts.draw_text(
                RIGHT_AMOUNT - fonts.text_width(date_str, FONT_SIZE_NORMAL),
                DATE_Y,
                date_str,
                FONT_SIZE_NORMAL,
                COLOR_LABEL,
                bold=False,
            )

        pdf.set_fill_color(*COLOR_BOX)
        _round_rect(pdf, BALANCE_BOX_X, BALANCE_BOX_Y, BALANCE_BOX_W, BALANCE_BOX_H, BOX_RADIUS, fill=True)

        balance_label = "Balance Due:"
        balance_value = _fmt_money(total, symbol)
        fonts.draw_text(
            DATE_LABEL_RIGHT - fonts.text_width(balance_label, FONT_SIZE_NORMAL),
            BALANCE_Y,
            balance_label,
            FONT_SIZE_NORMAL,
            COLOR_TITLE,
            bold=True,
        )
        fonts.draw_text(
            RIGHT_AMOUNT - fonts.text_width(balance_value, FONT_SIZE_NORMAL),
            BALANCE_Y,
            balance_value,
            FONT_SIZE_NORMAL,
            COLOR_TITLE,
            bold=True,
        )

    # Layout
    if len(items) <= FIRST_PAGE_CAPACITY:
        draw_header_full()
        draw_table_header(BAR_Y_FIRST, BAR_TEXT_Y_FIRST)
        draw_items(ITEMS_START_Y_FIRST, items, ITEM_ROW_H)
        draw_totals(TOTALS_START_Y_FIRST, TOTAL_ROW_H_FIRST)
        draw_notes(NOTES_LABEL_Y_FIRST, NOTES_TEXT_Y_FIRST, NOTES_LINE_H_FIRST)
    else:
        draw_header_full()
        draw_table_header(BAR_Y_FIRST, BAR_TEXT_Y_FIRST)
        draw_items(ITEMS_START_Y_FIRST, items[:FIRST_PAGE_CAPACITY], ITEM_ROW_H)

        remaining = items[FIRST_PAGE_CAPACITY:]
        while len(remaining) > LAST_PAGE_CAPACITY:
            take = min(MID_PAGE_CAPACITY, len(remaining) - LAST_PAGE_CAPACITY)
            pdf.add_page()
            draw_table_header(BAR_Y_CONT, BAR_TEXT_Y_CONT)
            draw_items(ITEMS_START_Y_CONT, remaining[:take], ITEM_ROW_H)
            remaining = remaining[take:]

        pdf.add_page()
        draw_table_header(BAR_Y_CONT, BAR_TEXT_Y_CONT)
        draw_items(ITEMS_START_Y_CONT, remaining, ITEM_ROW_H)
        draw_totals(TOTALS_START_Y_CONT, TOTAL_ROW_H_CONT)
        draw_notes(NOTES_LABEL_Y_CONT, NOTES_TEXT_Y_CONT, NOTES_LINE_H_CONT)

    return pdf.output(dest="S").encode("latin-1")


class InvoiceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path not in ("/", "/invoice", "/generate"):
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b""

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "invalid_json", "detail": str(exc)}).encode("utf-8"))
            return

        try:
            pdf_bytes = render_invoice(payload)
        except Exception as exc:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "render_failed", "detail": str(exc)}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), InvoiceHandler)
    print(f"Invoice API server listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    host = os.getenv("INVOICE_HOST", "0.0.0.0")
    port = int(os.getenv("INVOICE_PORT", "8080"))
    run(host, port)
