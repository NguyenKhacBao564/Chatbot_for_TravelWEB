import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

# Ánh xạ tiếng Việt sang số
MONTH_MAP = {
    "mười một": 11, "mười hai": 12,
    "một": 1, "hai": 2, "ba": 3, "tư": 4, "năm": 5, "sáu": 6,
    "bảy": 7, "tám": 8, "chín": 9, "mười": 10
}

DAY_OF_WEEK_MAP = {
    "thứ hai": 0, "thứ ba": 1, "thứ tư": 2, "thứ năm": 3,
    "thứ sáu": 4, "thứ bảy": 5, "chủ nhật": 6
}


def add_months(value, months):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, 28)
    return value.replace(year=year, month=month, day=day)

def is_valid_date(year, month, day=None):
    """Kiểm tra ngày tháng hợp lệ."""
    try:
        if day:
            datetime(year, month, day)
        else:
            datetime(year, month, 1)  # Kiểm tra tháng
        return True
    except ValueError:
        return False

def parse_relative_time(query, now=None):
    """Xử lý thời gian tương đối như 'ngày mai', 'tuần sau'."""
    if now is None:
        now = datetime.now()
    
    query = query.lower()
    if "ngày mai" in query:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif ("tuần sau" in query or "tuần tới" in query) and not any(day in query for day in DAY_OF_WEEK_MAP):
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
    elif "tháng tới" in query or "tháng sau" in query:
        return add_months(now, 1).strftime("%Y-%m")
    
    # Xử lý thứ trong tuần
    for day_name, day_index in DAY_OF_WEEK_MAP.items():
        if day_name in query:
            current_dow = now.weekday()
            days_until = (day_index - current_dow + 7) % 7
            if "tuần sau" in query or "tuần tới" in query:
                days_until = days_until or 7  # Nếu trùng ngày, chọn tuần sau
            return (now + timedelta(days=days_until)).strftime("%Y-%m-%d")
    
    return None

def extract_time(query, now=None):
    """Trích xuất ngày/tháng cụ thể từ truy vấn bằng regex."""
    if now is None:
        now = datetime.now()
    current_year = now.year

    # Regex patterns
    day_month_pattern = r"ngày\s*(\d{1,2})\s*tháng\s*(mười một|mười hai|một|hai|ba|tư|năm|sáu|bảy|tám|chín|mười|\d{1,2})(?!\s*(một|hai|ba))"
    month_pattern = r"tháng\s*(mười một|mười hai|một|hai|ba|tư|năm|sáu|bảy|tám|chín|mười|\d{1,2})(?!\s*(một|hai|ba))"
    date_pattern = r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?"
    year_pattern = r"năm\s*(\d{4})"

    # Trích xuất năm
    year_match = re.search(year_pattern, query, re.IGNORECASE)
    if year_match:
        current_year = int(year_match.group(1))

    # Trích xuất ngày-tháng
    day_month = re.search(day_month_pattern, query, re.IGNORECASE)
    if day_month:
        day = int(day_month.group(1))
        month_str = day_month.group(2).lower()
        month = MONTH_MAP.get(month_str)
        if month is None:
            try:
                month = int(month_str)
            except ValueError:
                return None
        if is_valid_date(current_year, month, day):
            return datetime(current_year, month, day).strftime("%Y-%m-%d")
        return None

    # Trích xuất tháng
    month = re.search(month_pattern, query, re.IGNORECASE)
    if month:
        month_str = month.group(1).lower()
        month_num = MONTH_MAP.get(month_str)
        if month_num is None:
            try:
                month_num = int(month_str)
            except ValueError:
                return None
        if is_valid_date(current_year, month_num):
            return datetime(current_year, month_num, 1).strftime("%Y-%m")
        return None

    # Trích xuất định dạng ngày/tháng (3/5 hoặc 3/5/2025)
    date = re.search(date_pattern, query, re.IGNORECASE)
    if date:
        day = int(date.group(1))
        month = int(date.group(2))
        year = date.group(3)
        if year:
            current_year = int(year)
        if is_valid_date(current_year, month, day):
            return datetime(current_year, month, day).strftime("%Y-%m-%d")
        return None

    return None

def extract_all_times(query, now=None):
    """
    Trích xuất thời gian từ truy vấn, kết hợp regex và thời gian tương đối.
    Args:
        query (str): Câu truy vấn tiếng Việt.
        now (datetime, optional): Thời điểm tham chiếu, mặc định là hiện tại.
    Returns:
        str | None: Ngày/tháng định dạng YYYY-MM-DD, YYYY-MM, hoặc None nếu không tìm thấy.
    """
    if not query or not isinstance(query, str):
        logger.error("Truy vấn không hợp lệ")
        return None

    if now is None:
        now = datetime.now()

    # Thử regex cho ngày/tháng cụ thể
    result = extract_time(query, now)
    if result:
        logger.info("Truy vấn: %s -> Thời gian (regex): %s", query, result)
        return result

    # Thử thời gian tương đối
    result = parse_relative_time(query, now)
    if result:
        logger.info("Truy vấn: %s -> Thời gian (tương đối): %s", query, result)
        return result

    logger.info("Truy vấn: %s -> Không tìm thấy thời gian", query)
    return None

# # Test với 50 truy vấn
# if __name__ == "__main__":
#     queries = [
#         "tôi muốn đặt tour đi đà lạt vào tháng 7",  # 2025-07
#         "tôi muốn đặt tour đi xuất phát từ ngày 3 tháng 5",  # 2025-05-03
#         "tôi muốn đi vào 3/5",  # 2025-05-03
#         "tôi muốn đặt tour ngày mai",  # 2025-05-19
#         "tôi muốn đặt tour tuần sau",  # 2025-05-25
#         "tôi muốn đặt tour tháng tới",  # 2025-06
#         "tôi muốn đặt tour thứ tư tuần sau",  # 2025-05-21
#         "tôi muốn đặt tour vào tháng ba năm 2026",  # 2026-03
#         "tôi muốn đi Đà Lạt",  # None
#         "tôi muốn đặt tour đi đà lạt vào tháng 7",  # 2025-07
#         "tôi muốn đặt tour đi xuất phát từ ngày 3 tháng 5",  # 2025-05-03
#         "tôi muốn đi vào 3/5",  # 2025-05-03
#         "tôi muốn đặt tour ngày mai",  # 2025-05-19
#         "tôi muốn đặt tour tuần sau",  # 2025-05-25
#         "tôi muốn đặt tour tháng sau",  # 2025-06
#         "tôi muốn đặt tour vào ngày 15 tháng 8",  # 2025-08-15
#         "tôi muốn đi vào 20-12",  # 2025-12-20
#         "đặt tour vào tháng mười",  # 2025-10
#         "tôi muốn đặt tour ngày 5 tháng mười một năm 2025",  # 2025-11-05
#         "tôi muốn đặt tour vào thứ hai tuần này",  # 2025-05-19
#         "tôi muốn đi tour vào 10/4/2025",  # 2025-04-10
#         "đặt tour tháng hai năm 2026",  # 2026-02
#         "tôi muốn đặt tour vào thứ sáu tuần sau",  # 2025-05-23
#         "tôi muốn đi vào ngày 30 tháng 4",  # 2025-04-30
#         "đặt tour vào tháng tư",  # 2025-04
#         "tôi muốn đặt tour vào 25-7",  # 2025-07-25
#         "tôi muốn đi tour ngày 1 tháng 1 năm 2026",  # 2026-01-01
#         "đặt tour vào thứ ba tuần sau",  # 2025-05-20
#         "tôi muốn đặt tour vào tháng chín năm 2024",  # 2024-09
#         "tôi muốn đi vào 15/8/2025",  # 2025-08-15
#         "tôi muốn đặt tour ngày 12 tháng sáu",  # 2025-06-12
#         "đặt tour vào tuần tới",  # 2025-05-25
#         "tôi muốn đi vào thứ năm tuần này",  # 2025-05-22
#         "tôi muốn đặt tour vào ngày 28 tháng 2 năm 2025",  # 2025-02-28
#         "đặt tour tháng mười hai",  # 2025-12
#         "tôi muốn đi tour vào 5-9",  # 2025-09-05
#         "tôi muốn đặt tour ngày 17 tháng bảy",  # 2025-07-17
#         "tôi muốn đi vào thứ bảy tuần sau",  # 2025-05-24
#         "đặt tour vào tháng một năm 2026",  # 2026-01
#         "tôi muốn đặt tour vào 1/5",  # 2025-05-01
#         "tôi muốn đi tour ngày 31 tháng 12 năm 2025",  # 2025-12-31
#         "tôi muốn đặt tour vào tháng tám",  # 2025-08
#         "tôi muốn đi vào thứ hai tuần tới",  # 2025-05-19
#         "tôi muốn đặt tour vào 20/11/2025",  # 2025-11-20
#         "đặt tour ngày 10 tháng chín",  # 2025-09-10
#         "tôi muốn đi tour không có ngày cụ thể",  # None
#         "tôi muốn đặt tour vào ngày 32 tháng 5",  # None
#         "đặt tour tháng mười ba",  # None
#         "tôi muốn đi vào 29/2/2025",  # None
#         "tôi muốn đặt tour ngày 22 tháng mười",  # 2025-10-22
#     ]
    
#     for q in queries:
#         result = extract_all_times(q)
#         print(f"Query: {q} -> Thời gian: {result}")
