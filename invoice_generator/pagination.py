"""Helpers for estimating invoice pagination constraints."""

from __future__ import annotations

from .pdf_constants import FIRST_PAGE_CAPACITY, LAST_PAGE_CAPACITY, MID_PAGE_CAPACITY


def estimate_page_count(item_count: int) -> int:
    if item_count <= FIRST_PAGE_CAPACITY:
        return 1
    remaining = item_count - FIRST_PAGE_CAPACITY
    if remaining <= LAST_PAGE_CAPACITY:
        return 2
    mid_items = remaining - LAST_PAGE_CAPACITY
    mid_pages = (mid_items + MID_PAGE_CAPACITY - 1) // MID_PAGE_CAPACITY
    return 2 + mid_pages


def max_items_for_pages(page_count: int) -> int:
    if page_count <= 1:
        return FIRST_PAGE_CAPACITY
    return FIRST_PAGE_CAPACITY + LAST_PAGE_CAPACITY + MID_PAGE_CAPACITY * (page_count - 2)
