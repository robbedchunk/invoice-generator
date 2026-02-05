import unittest

from invoice_generator.pagination import estimate_page_count, max_items_for_pages


class PaginationTests(unittest.TestCase):
    def test_estimate_page_count_boundary_values(self) -> None:
        self.assertEqual(estimate_page_count(0), 1)
        self.assertEqual(estimate_page_count(28), 1)
        self.assertEqual(estimate_page_count(29), 2)
        self.assertEqual(estimate_page_count(34), 2)
        self.assertEqual(estimate_page_count(35), 3)

    def test_max_items_for_pages_matches_capacity_rules(self) -> None:
        self.assertEqual(max_items_for_pages(1), 28)
        self.assertEqual(max_items_for_pages(2), 34)
        self.assertEqual(max_items_for_pages(3), 74)


if __name__ == "__main__":
    unittest.main()
