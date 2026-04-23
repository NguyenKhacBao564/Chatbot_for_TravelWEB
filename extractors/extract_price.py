import re


def parse_number(text):
    """Chuyển văn bản thành số, hỗ trợ số thập phân (VD: '1.5' hoặc '2,5')."""
    text = text.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", text):
        return float(re.sub(r"[.,]", "", text))
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0


def normalize_price_text(price_text):
    """Chuẩn hóa văn bản giá thành số nguyên dạng chuỗi."""
    price_text = price_text.lower().strip()
    price_text = re.sub(r"\s*(vnđ|vnd|đ|đồng)\s*", "", price_text)

    extra_value = 0.5 if "rưỡi" in price_text or "nửa" in price_text else 0
    price_text = price_text.replace("rưỡi", "").replace("nửa", "")

    units = {
        "k": 1000,
        "nghìn": 1000,
        "ngàn": 1000,
        "tr": 1000000,
        "triệu": 1000000,
        "m": 1000000,
        "tỷ": 1000000000,
        "tỉ": 1000000000,
    }

    numeric_match = re.search(r"(\d{1,3}(?:[\.,\s]\d{3})+|\d+(?:[\.,]\d+)?)", price_text)
    if not numeric_match:
        return price_text if price_text.isdigit() else "0"

    numeric_value = parse_number(numeric_match.group(1)) + extra_value

    unit_match = re.search(r"(triệu|nghìn|ngàn|tỷ|tỉ|tr|k|m)\b", price_text)
    if unit_match:
        unit = unit_match.group(1)
        multiplier = units.get(unit)
        if multiplier:
            return str(int(numeric_value * multiplier))

    return str(int(numeric_value))


def extract_price_values(query):
    """Return all price values found in a Vietnamese query as integers."""
    if not query or not isinstance(query, str):
        return []

    patterns = [
        r"(\d{1,3}(?:[\.,\s]\d{3})+|\d+)\s*(?:vnđ|vnd|đồng|đ)",
        r"(\d+(?:[\.,]\d+)?\s*(?:triệu|nghìn|ngàn|tỷ|tỉ|tr|k|m)\s*(?:rưỡi|nửa)?)",
        r"(?:giá|khoảng|tầm|chỉ từ|dưới|trên|ngân sách|budget|còn)\s*(\d+(?:[\.,]\d+)?\s*(?:triệu|nghìn|ngàn|tỷ|tỉ|tr|k|m)?\s*(?:rưỡi|nửa)?)",
        r"(?<!\d)(\d{5,})(?!\d)",
    ]

    prices = []
    for pattern in patterns:
        for match in re.findall(pattern, query, re.IGNORECASE):
            price_text = "".join(match) if isinstance(match, tuple) else match
            cleaned_price = normalize_price_text(price_text)
            if cleaned_price.isdigit():
                prices.append(int(cleaned_price))

    unique_prices = []
    for price in prices:
        if price > 0 and price not in unique_prices:
            unique_prices.append(price)
    return unique_prices


def extract_price_vn(query):
    """
    Trích xuất một giá tiền duy nhất từ câu truy vấn bằng rule-based parsing.
    Trả về số nguyên hoặc None nếu không tìm thấy.
    """
    prices = extract_price_values(query)
    return str(max(prices)) if prices else "None"
