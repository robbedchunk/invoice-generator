import unittest
from importlib import util as importlib_util

FPDF_AVAILABLE = importlib_util.find_spec("fpdf") is not None
if FPDF_AVAILABLE:
    from invoice_generator.rendering import render_invoice


@unittest.skipUnless(FPDF_AVAILABLE, "fpdf is not installed")
class RenderingTests(unittest.TestCase):
    def test_render_invoice_returns_pdf_bytes(self) -> None:
        payload = {
            "from": "ACME Inc.",
            "to": "Client LLC\n123 Main St\nCity, ST 12345",
            "number": "INV-001",
            "date": "2026-01-15",
            "items": [
                {"name": "Consulting", "quantity": 2, "unit_cost": 150.0},
            ],
            "currency": "USD",
        }

        pdf = render_invoice(payload)

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 100)


if __name__ == "__main__":
    unittest.main()
