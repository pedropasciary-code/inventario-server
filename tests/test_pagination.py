from app.services.pagination import build_pagination


def test_build_pagination_clamps_page_and_calculates_offset():
    pagination = build_pagination(total_items=30, page=99, per_page=10)

    assert pagination.page == 3
    assert pagination.total_pages == 3
    assert pagination.offset == 20
    assert pagination.first_item == 21
    assert pagination.has_previous_page is True
    assert pagination.has_next_page is False


def test_build_pagination_handles_empty_result_set():
    pagination = build_pagination(total_items=0, page=-1, per_page=25)

    assert pagination.page == 1
    assert pagination.total_pages == 1
    assert pagination.offset == 0
    assert pagination.first_item == 0
    assert pagination.has_previous_page is False
    assert pagination.has_next_page is False
