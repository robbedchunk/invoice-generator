"""Font discovery and text rendering helpers."""

from __future__ import annotations

import os
import threading
from typing import List, Optional, Tuple

from fpdf import FPDF  # type: ignore
import fpdf as fpdf_module

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cache parsed font metrics under /tmp, scoped by process to avoid cross-process write races.
FONT_CACHE_ROOT = os.getenv("INVOICE_FONT_CACHE_DIR", "/tmp/invoice-font-cache")
FONT_CACHE_DIR = os.path.join(FONT_CACHE_ROOT, str(os.getpid()))


def configure_fpdf_cache() -> None:
    try:
        os.makedirs(FONT_CACHE_DIR, exist_ok=True)
        fpdf_module.FPDF_CACHE_MODE = 2
        fpdf_module.FPDF_CACHE_DIR = FONT_CACHE_DIR
    except Exception:
        # Fallback to no-cache mode if /tmp is unavailable in the runtime.
        fpdf_module.FPDF_CACHE_MODE = 1


configure_fpdf_cache()


def find_font_path(env_var: str, candidates: List[str]) -> Optional[str]:
    override = os.getenv(env_var)
    if override and os.path.exists(override):
        return override

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


FONT_INIT_LOCK = threading.Lock()


class FontManager:
    FAMILY = "InvoiceFont"
    BUNDLED_REGULAR = os.path.join(_PROJECT_ROOT, "fonts", "DejaVuSans.ttf")
    BUNDLED_BOLD = os.path.join(_PROJECT_ROOT, "fonts", "DejaVuSans-Bold.ttf")
    SYSTEM_REGULAR_CANDIDATES = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
    ]
    SYSTEM_BOLD_CANDIDATES = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/DejaVuSans-Bold.ttf",
    ]

    def __init__(self, pdf: FPDF) -> None:
        self.pdf = pdf
        self.family = self.FAMILY
        self.has_bold = False

        regular_path = find_font_path(
            "INVOICE_FONT_PATH",
            [self.BUNDLED_REGULAR, *self.SYSTEM_REGULAR_CANDIDATES],
        )
        if not regular_path:
            raise RuntimeError(
                "Unicode font not found. Set INVOICE_FONT_PATH to a valid TTF file."
            )

        bold_path = find_font_path(
            "INVOICE_FONT_BOLD_PATH",
            [self.BUNDLED_BOLD, *self.SYSTEM_BOLD_CANDIDATES],
        )

        with FONT_INIT_LOCK:
            self.pdf.add_font(self.FAMILY, "", regular_path, uni=True)
            if bold_path:
                self.pdf.add_font(self.FAMILY, "B", bold_path, uni=True)
                self.has_bold = True

    def set_font(self, size: int) -> None:
        self.pdf.set_font(self.family, "", size)

    def text_width(self, text: str, size: int, bold: bool = False) -> float:
        style = "B" if bold and self.has_bold else ""
        self.pdf.set_font(self.family, style, size)
        return self.pdf.get_string_width(text)

    def draw_text(
        self,
        x: float,
        y: float,
        text: str,
        size: int,
        color: Tuple[int, int, int],
        bold: bool = False,
    ) -> None:
        self.pdf.set_text_color(*color)
        style = "B" if bold and self.has_bold else ""
        self.pdf.set_font(self.family, style, size)
        if bold and not self.has_bold:
            self.pdf.text(x, y, text)
            self.pdf.text(x + 0.4, y, text)
        else:
            self.pdf.text(x, y, text)
