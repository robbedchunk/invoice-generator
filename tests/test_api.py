import json
import unittest
from unittest.mock import patch

from invoice_generator.server import validate_invoice_payload


class ApiValidationTests(unittest.TestCase):
    def _json_bytes(self, payload: object) -> bytes:
        return json.dumps(payload).encode("utf-8")

    def test_accepts_valid_payload(self) -> None:
        payload, error = validate_invoice_payload(
            self._json_bytes({"items": [{"name": "Work", "quantity": 1, "unit_cost": 20}]}),
            max_pages=100,
        )

        self.assertIsNone(error)
        assert payload is not None
        self.assertIn("items", payload)

    def test_rejects_invalid_utf8(self) -> None:
        _, error = validate_invoice_payload(b"\xff", max_pages=100)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], 400)
        self.assertEqual(error[1]["error"], "invalid_encoding")

    def test_rejects_invalid_json(self) -> None:
        _, error = validate_invoice_payload(b'{"items":', max_pages=100)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], 400)
        self.assertEqual(error[1]["error"], "invalid_json")

    def test_rejects_non_object_root(self) -> None:
        _, error = validate_invoice_payload(self._json_bytes(["bad-root"]), max_pages=100)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], 400)
        self.assertEqual(error[1]["error"], "invalid_payload")

    def test_rejects_non_array_items(self) -> None:
        _, error = validate_invoice_payload(self._json_bytes({"items": "bad"}), max_pages=100)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], 400)
        self.assertEqual(error[1]["error"], "invalid_payload")

    def test_rejects_payload_exceeding_max_pages(self) -> None:
        with patch("invoice_generator.server.estimate_page_count", return_value=11):
            _, error = validate_invoice_payload(self._json_bytes({"items": []}), max_pages=10)

        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error[0], 413)
        self.assertEqual(error[1]["error"], "invoice_too_large")
        self.assertIn("max_items", error[1])


if __name__ == "__main__":
    unittest.main()
