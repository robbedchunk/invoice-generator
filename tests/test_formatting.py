import unittest

from invoice_generator.formatting import fmt_date, fmt_qty, safe_float, split_lines


class FormattingTests(unittest.TestCase):
    def test_fmt_date_formats_valid_dates(self) -> None:
        self.assertEqual(fmt_date("2026-01-15"), "Jan 15, 2026")

    def test_fmt_date_returns_original_for_invalid_input(self) -> None:
        raw = "not-a-date"
        self.assertEqual(fmt_date(raw), raw)

    def test_fmt_qty_handles_integer_and_float_values(self) -> None:
        self.assertEqual(fmt_qty(3), "3")
        self.assertEqual(fmt_qty(2.5), "2.5")

    def test_safe_float_uses_default_for_non_numeric_values(self) -> None:
        self.assertEqual(safe_float("abc", 7.5), 7.5)

    def test_split_lines_ignores_blank_lines(self) -> None:
        self.assertEqual(split_lines("a\n\n b \n"), ["a", " b "])


if __name__ == "__main__":
    unittest.main()
