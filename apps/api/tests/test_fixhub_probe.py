"""Live E2E probe for FixHub (temporary)."""
from app.core.pagination import paginate


def test_total_pages_counts_partial_page():
    assert paginate(1, 25, 95)["total_pages"] == 4


def test_offset_first_page():
    assert paginate(1, 25, 95)["offset"] == 0
