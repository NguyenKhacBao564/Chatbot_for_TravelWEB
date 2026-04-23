import re
from google import genai
from google.genai import types
from google_genAI import get_genai_response

def parse_number(text):
    """Chuyển văn bản thành số, hỗ trợ số thập phân (VD: '1.5' hoặc '2,5')."""
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0

def normalize_price_text(price_text):
    """Chuẩn hóa văn bản giá thành số nguyên dạng chuỗi."""
    price_text = price_text.lower().strip()
    price_text = re.sub(r"\s*(vnđ|vnd|đ|đồng)\s*", "", price_text)  # Xóa đơn vị tiền tệ

    # Xử lý "rưỡi" hoặc "nửa" (0.5)
    extra_value = 0.5 if "rưỡi" in price_text or "nửa" in price_text else 0
    price_text = price_text.replace("rưỡi", "").replace("nửa", "")

    # Ánh xạ đơn vị
    units = {"k": 1000, "tr": 1000000, "triệu": 1000000, "tỷ": 1000000000, "tỉ": 1000000000}

    # Tìm phần số
    numeric_match = re.search(r"(\d+[\.,]?\d*)", price_text)
    if not numeric_match:
        return price_text if price_text.isdigit() else "0"

    numeric_value = parse_number(numeric_match.group(1)) + extra_value

    # Áp dụng đơn vị
    for unit, multiplier in units.items():
        if unit in price_text:
            return str(int(numeric_value * multiplier))

    return str(int(numeric_value))

def extract_price_vn(query):
    """
    Trích xuất một giá tiền duy nhất từ câu truy vấn, ưu tiên dùng Gemini.
    Trả về số nguyên hoặc None nếu không tìm thấy.
    """
    # Sử dụng Gemini trước
    genai_prompt = (
        f"Từ câu sau đây, hãy trích xuất TẤT CẢ các giá tiền dưới dạng số, ví dụ: 100000, 2500000. "
        f"Nếu có nhiều giá, phân tách chúng bằng dấu phẩy. "
        f"Nếu giá có đơn vị như 'k', 'triệu', 'tỷ', hãy quy đổi về giá trị đầy đủ (ví dụ: 100k -> 100000, 1.5 triệu -> 1500000). "
        f"Nếu là một khoảng giá (ví dụ 'từ A đến B'), hãy trả về cả hai giá trị A và B, phân tách bằng dấu phẩy. "
        f"Câu cần trích xuất: '{query}'. "
        f"Chỉ trả về các số đã quy đổi, phân tách bằng dấu phẩy nếu có nhiều. Nếu không có giá nào, trả về 'None'."
    )
    genai_result = get_genai_response(genai_prompt)
    print(f"Kết quả từ Gemini: {genai_result}")

    # Xử lý kết quả từ Gemini
    if genai_result and "None" not in genai_result:
        cleaned_price = normalize_price_text(genai_result.strip())
        if cleaned_price.isdigit():
            return cleaned_price

    # Dự phòng bằng regex
    patterns = [
        r"(\d{1,3}(?:[\.,\s]\d{3})*(?:[\.,]\d+)?)\s*(?:vnđ|vnd|đồng|đ)",
        r"(\d+[\.,]?\d*\s*(?:k|tr(?:iệu)?|t[ỷy])(?:\s*(rưỡi|nửa))?)",
        r"(?:giá|khoảng|tầm|chỉ từ|còn)\s*(\d+[\.,]?\d*\s*(?:k|tr(?:iệu)?|t[ỷy])(?:\s*(rưỡi|nửa))?)",
        r"(?<!\d)(\d{4,})(?!\d)"
    ]

    final_prices = []
    for pattern in patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            price_text = "".join(m for m in match if m) if isinstance(match, tuple) else match
            cleaned_price = normalize_price_text(price_text)
            if cleaned_price.isdigit():
                final_prices.append(cleaned_price)
    result = max(final_prices) if final_prices else "None"
    return result
