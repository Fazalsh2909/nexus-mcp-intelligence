"""Pagination helpers for list endpoints."""


def paginate(page: int, per_page: int, total: int) -> dict[str, int]:
    """Return offset/limit/total_pages for 1-indexed pages."""
    page = max(1, page)
    per_page = max(1, per_page)
    offset = (page - 1) * per_page
    total_pages = max(1, (total + per_page - 1) // per_page)
    return {"offset": offset, "limit": per_page, "total_pages": total_pages}
