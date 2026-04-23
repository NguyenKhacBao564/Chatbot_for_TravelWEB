from datetime import datetime

from extractors.extract_time import extract_all_times


def test_extract_month_with_year():
    assert extract_all_times("Tôi muốn đi tháng 12 năm 2026") == "2026-12"


def test_extract_specific_date():
    assert extract_all_times("Khởi hành ngày 5 tháng 6 năm 2026") == "2026-06-05"


def test_extract_relative_tomorrow():
    now = datetime(2026, 4, 23)
    assert extract_all_times("Tôi muốn đặt tour ngày mai", now=now) == "2026-04-24"


def test_extract_time_returns_none_when_missing():
    assert extract_all_times("Tôi muốn đi tour không có ngày cụ thể") is None
