from extractors.extract_price import extract_price_values, extract_price_vn


def test_extract_price_million_budget():
    assert extract_price_vn("Tôi muốn đi Đà Lạt khoảng 5 triệu") == "5000000"


def test_extract_price_short_million_budget():
    assert extract_price_vn("ngân sách 3tr") == "3000000"


def test_extract_price_half_million():
    assert extract_price_vn("Tour tầm 2 triệu rưỡi có không?") == "2500000"


def test_extract_price_range_values():
    assert extract_price_values("Tìm tour từ 3 triệu đến 5 triệu") == [3000000, 5000000]


def test_extract_price_short_units():
    assert extract_price_vn("Tour 1500k đi đâu được?") == "1500000"


def test_extract_price_returns_none_when_missing():
    assert extract_price_vn("Tôi muốn đi tour giá hợp lý") is None


def test_extract_price_ignores_age_people_and_duration_counts():
    assert extract_price_vn("Trẻ em dưới 5 tuổi có phải mua vé không?") is None
    assert extract_price_vn("Tôi đi 2 người") is None
    assert extract_price_vn("Tour 3 ngày có lịch trình thế nào?") is None


def test_extract_price_does_not_treat_year_before_tren_as_million_unit():
    assert extract_price_values("Tìm tour Đà Lạt tháng 5 năm 2026 trên 5tr") == [5000000]
    assert extract_price_values("Tìm tour Đà Lạt tháng 5 năm 2026 dưới 5 triệu") == [5000000]
