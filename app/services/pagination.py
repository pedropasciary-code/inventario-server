from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pagination:
    page: int
    per_page: int
    total_pages: int
    offset: int
    first_item: int
    has_previous_page: bool
    has_next_page: bool


def build_pagination(total_items: int, page: int, per_page: int) -> Pagination:
    total_pages = max(math.ceil(total_items / per_page), 1)
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * per_page
    return Pagination(
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        offset=offset,
        first_item=offset + 1 if total_items else 0,
        has_previous_page=page > 1,
        has_next_page=page < total_pages,
    )
