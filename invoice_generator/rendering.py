"""Invoice PDF rendering logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF  # type: ignore

from .fonts import FontManager
from .formatting import fmt_date, fmt_money, fmt_qty, round_rect, safe_float, split_lines, wrap_text
from .pdf_constants import (
    ADDR_LINE_H,
    BALANCE_BOX_H,
    BALANCE_BOX_W,
    BALANCE_BOX_X,
    BALANCE_BOX_Y,
    BALANCE_Y,
    BAR_H,
    BAR_RADIUS,
    BAR_TEXT_Y_CONT,
    BAR_TEXT_Y_FIRST,
    BAR_W,
    BAR_Y_CONT,
    BAR_Y_FIRST,
    BILL_TO_ADDR_Y,
    BILL_TO_LABEL_Y,
    BILL_TO_NAME_Y,
    BOX_RADIUS,
    COLOR_BAR,
    COLOR_BAR_TEXT,
    COLOR_BILLTO,
    COLOR_BOX,
    COLOR_INVOICE_NUM,
    COLOR_ITEM,
    COLOR_LABEL,
    COLOR_NOTES,
    COLOR_NUM,
    COLOR_TEXT,
    COLOR_TEXT_ALT,
    COLOR_TITLE,
    DATE_LABEL_RIGHT,
    DATE_Y,
    DEFAULT_CURRENCY_SYMBOLS,
    FIRST_PAGE_CAPACITY,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    ITEM_ROW_H,
    ITEMS_START_Y_CONT,
    ITEMS_START_Y_FIRST,
    ITEM_TO_QTY_GUTTER,
    LABEL_RIGHT,
    LAST_PAGE_CAPACITY,
    MID_PAGE_CAPACITY,
    NAME_LINE_H,
    NAME_Y,
    NOTES_LABEL_Y_CONT,
    NOTES_LABEL_Y_FIRST,
    NOTES_LINE_H_CONT,
    NOTES_LINE_H_FIRST,
    NOTES_TEXT_Y_CONT,
    NOTES_TEXT_Y_FIRST,
    NUMBER_RIGHT,
    NUMBER_Y,
    PAGE_H,
    RATE_RIGHT,
    RIGHT_AMOUNT,
    TITLE_RIGHT,
    TITLE_Y,
    TOTAL_ROW_H_CONT,
    TOTAL_ROW_H_FIRST,
    TOTALS_START_Y_CONT,
    TOTALS_START_Y_FIRST,
    X_BAR,
    X_ITEM,
    X_LEFT,
)


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal: float
    discount_value: float
    total: float
    discount_label: Optional[str]
    currency_symbol: str


class InvoiceRenderer:
    qty_center = 375
    rate_center = 457
    amount_center = 531

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data
        self.pdf = FPDF(unit="pt", format="letter")
        self.pdf.set_auto_page_break(False)
        self.pdf.add_page()

        self.fonts = FontManager(self.pdf)
        self.items = data.get("items", []) or []
        self.totals = self._calculate_totals()

    def _calculate_totals(self) -> InvoiceTotals:
        currency = str(self.data.get("currency", "USD")).upper()
        symbol = DEFAULT_CURRENCY_SYMBOLS.get(currency, "$" if currency == "USD" else f"{currency} ")

        subtotal = 0.0
        for item in self.items:
            qty = safe_float(item.get("quantity", 1), 1.0)
            unit_cost = safe_float(item.get("unit_cost", 0.0), 0.0)
            subtotal += qty * unit_cost

        discounts = self.data.get("discounts", 0)
        discount_value = 0.0
        discount_label = None
        if discounts:
            try:
                discount_value = float(discounts)
            except Exception:
                discount_value = 0.0

            fields = self.data.get("fields", {}) or {}
            if fields.get("discounts") == "%":
                discount_value = subtotal * (discount_value / 100.0)
                d_display = int(discounts) if float(discounts).is_integer() else discounts
                discount_label = f"Discount ({d_display}%):"
            else:
                discount_label = "Discount:"

        total = subtotal - discount_value
        return InvoiceTotals(
            subtotal=subtotal,
            discount_value=discount_value,
            total=total,
            discount_label=discount_label,
            currency_symbol=symbol,
        )

    def _draw_table_header(self, bar_y: float, text_y: float) -> None:
        self.pdf.set_fill_color(*COLOR_BAR)
        round_rect(self.pdf, X_BAR, bar_y, BAR_W, BAR_H, BAR_RADIUS, fill=True)

        self.fonts.draw_text(X_ITEM, text_y, "Item", FONT_SIZE_SMALL, COLOR_BAR_TEXT, bold=True)
        qty_label = "Quantity"
        rate_label = "Rate"
        amount_label = "Amount"

        self.fonts.draw_text(
            self.qty_center - self.fonts.text_width(qty_label, FONT_SIZE_SMALL) / 2.0,
            text_y,
            qty_label,
            FONT_SIZE_SMALL,
            COLOR_BAR_TEXT,
            bold=True,
        )
        self.fonts.draw_text(
            self.rate_center - self.fonts.text_width(rate_label, FONT_SIZE_SMALL) / 2.0,
            text_y,
            rate_label,
            FONT_SIZE_SMALL,
            COLOR_BAR_TEXT,
            bold=True,
        )
        self.fonts.draw_text(
            self.amount_center - self.fonts.text_width(amount_label, FONT_SIZE_SMALL) / 2.0,
            text_y,
            amount_label,
            FONT_SIZE_SMALL,
            COLOR_BAR_TEXT,
            bold=True,
        )

    def _draw_items(self, start_y: float, page_items: List[Dict[str, Any]], row_h: float) -> float:
        max_name_width = self.qty_center - X_ITEM - ITEM_TO_QTY_GUTTER
        y = start_y

        for item in page_items:
            name = str(item.get("name", "")).strip()
            qty = safe_float(item.get("quantity", 1), 1.0)
            unit_cost = safe_float(item.get("unit_cost", 0.0), 0.0)
            amount = qty * unit_cost

            num_name_lines = 1
            if name:
                paragraphs = name.split("\n")
                all_lines: List[Tuple[str, bool]] = []
                for paragraph_index, paragraph in enumerate(paragraphs):
                    paragraph = paragraph.strip()
                    if not paragraph:
                        continue
                    is_first_paragraph = paragraph_index == 0
                    wrapped = wrap_text(
                        self.fonts,
                        paragraph,
                        max_name_width,
                        FONT_SIZE_NORMAL,
                        bold=is_first_paragraph,
                    )
                    for line in wrapped:
                        all_lines.append((line, is_first_paragraph))

                num_name_lines = len(all_lines) if all_lines else 1
                for i, (line, is_bold) in enumerate(all_lines):
                    self.fonts.draw_text(
                        X_ITEM,
                        y + i * NAME_LINE_H,
                        line,
                        FONT_SIZE_NORMAL,
                        COLOR_ITEM,
                        bold=is_bold,
                    )

            qty_text = fmt_qty(qty)
            rate_text = fmt_money(unit_cost, self.totals.currency_symbol)
            amount_text = fmt_money(amount, self.totals.currency_symbol)

            self.fonts.draw_text(
                self.qty_center - self.fonts.text_width(qty_text, FONT_SIZE_NORMAL) / 2.0,
                y,
                qty_text,
                FONT_SIZE_NORMAL,
                COLOR_NUM,
                bold=False,
            )
            self.fonts.draw_text(
                RATE_RIGHT - self.fonts.text_width(rate_text, FONT_SIZE_NORMAL),
                y,
                rate_text,
                FONT_SIZE_NORMAL,
                COLOR_NUM,
                bold=False,
            )
            self.fonts.draw_text(
                RIGHT_AMOUNT - self.fonts.text_width(amount_text, FONT_SIZE_NORMAL),
                y,
                amount_text,
                FONT_SIZE_NORMAL,
                COLOR_NUM,
                bold=False,
            )

            y += (num_name_lines - 1) * NAME_LINE_H + row_h

        return y

    def _draw_totals(self, start_y: float, row_h: float) -> None:
        totals_y = start_y

        self.fonts.draw_text(
            LABEL_RIGHT - self.fonts.text_width("Subtotal:", FONT_SIZE_NORMAL),
            totals_y,
            "Subtotal:",
            FONT_SIZE_NORMAL,
            (118, 118, 118),
            bold=False,
        )
        self.fonts.draw_text(
            RIGHT_AMOUNT
            - self.fonts.text_width(
                fmt_money(self.totals.subtotal, self.totals.currency_symbol),
                FONT_SIZE_NORMAL,
            ),
            totals_y,
            fmt_money(self.totals.subtotal, self.totals.currency_symbol),
            FONT_SIZE_NORMAL,
            COLOR_NUM,
            bold=False,
        )

        totals_y += row_h
        if self.totals.discount_label:
            self.fonts.draw_text(
                LABEL_RIGHT - self.fonts.text_width(self.totals.discount_label, FONT_SIZE_NORMAL),
                totals_y,
                self.totals.discount_label,
                FONT_SIZE_NORMAL,
                (118, 118, 118),
                bold=False,
            )
            self.fonts.draw_text(
                RIGHT_AMOUNT
                - self.fonts.text_width(
                    fmt_money(self.totals.discount_value, self.totals.currency_symbol),
                    FONT_SIZE_NORMAL,
                ),
                totals_y,
                fmt_money(self.totals.discount_value, self.totals.currency_symbol),
                FONT_SIZE_NORMAL,
                COLOR_NUM,
                bold=False,
            )
            totals_y += row_h

        self.fonts.draw_text(
            LABEL_RIGHT - self.fonts.text_width("Total:", FONT_SIZE_NORMAL),
            totals_y,
            "Total:",
            FONT_SIZE_NORMAL,
            (118, 118, 118),
            bold=False,
        )
        self.fonts.draw_text(
            RIGHT_AMOUNT
            - self.fonts.text_width(
                fmt_money(self.totals.total, self.totals.currency_symbol),
                FONT_SIZE_NORMAL,
            ),
            totals_y,
            fmt_money(self.totals.total, self.totals.currency_symbol),
            FONT_SIZE_NORMAL,
            COLOR_NUM,
            bold=False,
        )

    def _draw_notes(self, label_y: float, text_y: float, line_h: float) -> None:
        notes = str(self.data.get("notes", "")).strip()
        if not notes:
            return

        page_bottom = PAGE_H - 30
        continuation_top = 30.0

        self.fonts.draw_text(X_ITEM, label_y, "Notes:", FONT_SIZE_NORMAL, COLOR_TEXT, bold=False)
        note_lines = split_lines(notes)

        y = text_y
        for line in note_lines:
            if y > page_bottom:
                self.pdf.add_page()
                y = continuation_top
            self.fonts.draw_text(X_ITEM, y, line, FONT_SIZE_NORMAL, COLOR_NOTES, bold=False)
            y += line_h

    def _draw_header_full(self) -> None:
        sender = str(self.data.get("from", "")).strip()
        if sender:
            self.fonts.draw_text(X_LEFT, NAME_Y, sender, FONT_SIZE_NORMAL, COLOR_TEXT, bold=True)

        self.fonts.draw_text(
            TITLE_RIGHT - self.fonts.text_width("INVOICE", FONT_SIZE_TITLE),
            TITLE_Y,
            "INVOICE",
            FONT_SIZE_TITLE,
            COLOR_TITLE,
            bold=False,
        )

        number = str(self.data.get("number", "")).strip()
        if number:
            invoice_number = f"# {number}"
            self.fonts.draw_text(
                NUMBER_RIGHT - self.fonts.text_width(invoice_number, FONT_SIZE_NORMAL),
                NUMBER_Y,
                invoice_number,
                FONT_SIZE_NORMAL,
                COLOR_INVOICE_NUM,
                bold=False,
            )

        to_block = split_lines(str(self.data.get("to", "")).strip())
        if to_block:
            self.fonts.draw_text(
                X_LEFT,
                BILL_TO_LABEL_Y,
                "Bill To:",
                FONT_SIZE_SMALL,
                COLOR_BILLTO,
                bold=False,
            )
            if len(to_block) > 0:
                self.fonts.draw_text(X_LEFT, BILL_TO_NAME_Y, to_block[0], FONT_SIZE_NORMAL, COLOR_TEXT, bold=True)
            if len(to_block) > 1:
                self.fonts.draw_text(X_LEFT, BILL_TO_ADDR_Y, to_block[1], FONT_SIZE_SMALL, COLOR_TEXT_ALT, bold=False)
            if len(to_block) > 2:
                self.fonts.draw_text(
                    X_LEFT,
                    BILL_TO_ADDR_Y + ADDR_LINE_H,
                    to_block[2],
                    FONT_SIZE_SMALL,
                    COLOR_TEXT_ALT,
                    bold=False,
                )
            if len(to_block) > 3:
                for i, line in enumerate(to_block[3:], start=2):
                    self.fonts.draw_text(
                        X_LEFT,
                        BILL_TO_ADDR_Y + ADDR_LINE_H * (i + 1),
                        line,
                        FONT_SIZE_SMALL,
                        COLOR_TEXT_ALT,
                        bold=False,
                    )

        date_str = fmt_date(str(self.data.get("date", "")))
        if date_str:
            self.fonts.draw_text(
                DATE_LABEL_RIGHT - self.fonts.text_width("Date:", FONT_SIZE_NORMAL),
                DATE_Y,
                "Date:",
                FONT_SIZE_NORMAL,
                COLOR_LABEL,
                bold=False,
            )
            self.fonts.draw_text(
                RIGHT_AMOUNT - self.fonts.text_width(date_str, FONT_SIZE_NORMAL),
                DATE_Y,
                date_str,
                FONT_SIZE_NORMAL,
                COLOR_LABEL,
                bold=False,
            )

        self.pdf.set_fill_color(*COLOR_BOX)
        round_rect(
            self.pdf,
            BALANCE_BOX_X,
            BALANCE_BOX_Y,
            BALANCE_BOX_W,
            BALANCE_BOX_H,
            BOX_RADIUS,
            fill=True,
        )

        balance_label = "Balance Due:"
        balance_value = fmt_money(self.totals.total, self.totals.currency_symbol)
        self.fonts.draw_text(
            DATE_LABEL_RIGHT - self.fonts.text_width(balance_label, FONT_SIZE_NORMAL),
            BALANCE_Y,
            balance_label,
            FONT_SIZE_NORMAL,
            COLOR_TITLE,
            bold=True,
        )
        self.fonts.draw_text(
            RIGHT_AMOUNT - self.fonts.text_width(balance_value, FONT_SIZE_NORMAL),
            BALANCE_Y,
            balance_value,
            FONT_SIZE_NORMAL,
            COLOR_TITLE,
            bold=True,
        )

    def _draw_single_page_layout(self) -> None:
        self._draw_header_full()
        self._draw_table_header(BAR_Y_FIRST, BAR_TEXT_Y_FIRST)
        items_end_y = self._draw_items(ITEMS_START_Y_FIRST, self.items, ITEM_ROW_H)

        totals_y = max(TOTALS_START_Y_FIRST, items_end_y + ITEM_ROW_H)
        self._draw_totals(totals_y, TOTAL_ROW_H_FIRST)

        totals_rows = 3 if self.totals.discount_label else 2
        totals_end_y = totals_y + (totals_rows - 1) * TOTAL_ROW_H_FIRST
        notes_gap = NOTES_LABEL_Y_FIRST - (TOTALS_START_Y_FIRST + 2 * TOTAL_ROW_H_FIRST)
        notes_label_y = max(NOTES_LABEL_Y_FIRST, totals_end_y + notes_gap)
        notes_text_y = notes_label_y + (NOTES_TEXT_Y_FIRST - NOTES_LABEL_Y_FIRST)
        self._draw_notes(notes_label_y, notes_text_y, NOTES_LINE_H_FIRST)

    def _draw_multi_page_layout(self) -> None:
        self._draw_header_full()
        self._draw_table_header(BAR_Y_FIRST, BAR_TEXT_Y_FIRST)
        self._draw_items(ITEMS_START_Y_FIRST, self.items[:FIRST_PAGE_CAPACITY], ITEM_ROW_H)

        cursor = FIRST_PAGE_CAPACITY
        last_page_start = len(self.items) - LAST_PAGE_CAPACITY
        while cursor < last_page_start:
            take = min(MID_PAGE_CAPACITY, last_page_start - cursor)
            self.pdf.add_page()
            self._draw_table_header(BAR_Y_CONT, BAR_TEXT_Y_CONT)
            self._draw_items(ITEMS_START_Y_CONT, self.items[cursor : cursor + take], ITEM_ROW_H)
            cursor += take

        self.pdf.add_page()
        self._draw_table_header(BAR_Y_CONT, BAR_TEXT_Y_CONT)
        self._draw_items(ITEMS_START_Y_CONT, self.items[cursor:], ITEM_ROW_H)
        self._draw_totals(TOTALS_START_Y_CONT, TOTAL_ROW_H_CONT)
        self._draw_notes(NOTES_LABEL_Y_CONT, NOTES_TEXT_Y_CONT, NOTES_LINE_H_CONT)

    def render(self) -> bytes:
        if len(self.items) <= FIRST_PAGE_CAPACITY:
            self._draw_single_page_layout()
        else:
            self._draw_multi_page_layout()

        pdf_blob = self.pdf.output(dest="S")
        if isinstance(pdf_blob, (bytes, bytearray)):
            return bytes(pdf_blob)
        if isinstance(pdf_blob, str):
            try:
                return pdf_blob.encode("latin-1")
            except UnicodeEncodeError as exc:
                raise RuntimeError(
                    "PDF serialization failed due to non-Latin-1 content. "
                    "Check Unicode font configuration (INVOICE_FONT_PATH/INVOICE_FONT_BOLD_PATH)."
                ) from exc
        raise RuntimeError(f"Unexpected PDF output type: {type(pdf_blob).__name__}")


def render_invoice(data: Dict[str, Any]) -> bytes:
    return InvoiceRenderer(data).render()
