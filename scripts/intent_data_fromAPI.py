#!/usr/bin/env python
# coding: utf-8
"""
create_dataset.py – sinh bộ dữ liệu intent cho chatbot tour du lịch
"""

import os
import json
import logging
import random
import argparse
import time
import re
from typing import List, Dict

from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
import google.generativeai as genai

# ─────────────────────────────── Logging ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────── Cấu hình API KEY ───────────────────────────
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("Không tìm thấy GOOGLE_API_KEY trong biến môi trường")
    raise ValueError("Cần thiết lập GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ─────────────────────────── Dữ liệu tĩnh ──────────────────────────────
GROUPS = {
    "north":  ["Hà Nội", "Hải Phòng", "Bắc Giang", "Bắc Kạn", "Cao Bằng",
               "Hà Giang", "Lạng Sơn", "Phú Thọ", "Quảng Ninh", "Thái Nguyên",
               "Tuyên Quang", "Lào Cai", "Yên Bái", "Điện Biên", "Hòa Bình",
               "Lai Châu", "Sơn La", "Bắc Ninh", "Hà Nam", "Hải Dương",
               "Hưng Yên", "Thái Bình", "Nam Định", "Ninh Bình", "Vĩnh Phúc"],
    "central": ["Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị",
                "Thừa Thiên Huế", "Đà Nẵng", "Quảng Nam", "Quảng Ngãi",
                "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận"],
    "south":  ["TP Hồ Chí Minh", "Cần Thơ", "An Giang", "Bạc Liêu", "Bến Tre",
               "Cà Mau", "Đồng Tháp", "Hậu Giang", "Kiên Giang", "Long An",
               "Sóc Trăng", "Tiền Giang", "Trà Vinh", "Vĩnh Long",
               "Bà Rịa–Vũng Tàu", "Bình Dương", "Bình Phước", "Đồng Nai",
               "Tây Ninh", "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông",
               "Lâm Đồng"]
}

TIME_EXPRESSIONS = [
    # ngày/ tháng/ sự kiện cố định
    "01/01", "30/04", "01/05", "02/09", "24/12", "14/02", "08/03", "20/11",
    "01/06", "10/10", "15/7/2025", "1/1/2026",
    "ngày 15 tháng 5", "ngày 2 tháng 9", "ngày mồng 3 Tết",
    # thứ – tuần
    "thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật",
    "thứ Hai tuần sau", "thứ Sáu tuần này", "Chủ nhật tới",
    "tuần này", "tuần tới", "tuần thứ 3 tháng 7",
    # tháng
    *[f"tháng {i}" for i in range(1, 13)],
    "đầu tháng 7", "cuối tháng 9",
    # quý
    "quý 1", "quý I", "quý 2", "quý 3", "quý 4",
    # mùa
    "mùa xuân", "mùa hè", "mùa thu", "mùa đông",
    # tương đối
    "ngày mai", "hôm nay", "cuối tuần này", "2 tuần nữa",
    "tháng tới", "năm sau", "cuối năm", "đầu năm sau",
    "khoảng tháng 7", "giữa tháng 8", "đầu quý 2", "cuối quý 3"
]

def random_money_expression() -> str:
    amt = round(random.uniform(1, 20), 1)
    int_amt = int(round(amt))
    return random.choice([
        f"{amt} triệu đồng",      f"{int_amt} triệu",        f"{int_amt}tr",
        f"{str(amt).replace('.', ',')} triệu",
        f"{int_amt*1000:,} nghìn", f"{int_amt*1000}k",
        f"{int(int_amt*1e6)}đ",    f"dưới {int_amt} triệu",
        f"khoảng {int_amt} triệu", f"= {int_amt}tr"
    ])

def random_time_expression() -> str:
    if random.random() < 0.7:
        return random.choice(TIME_EXPRESSIONS)
    mode = random.choice(["month_relative", "weekday_relative", "date_future"])
    if mode == "month_relative":
        return f"{random.choice(['đầu', 'giữa', 'cuối', 'khoảng'])} tháng {random.randint(1,12)}"
    if mode == "weekday_relative":
        weekday = random.choice(
            ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]
        )
        return f"{weekday} {random.choice(['tuần sau', 'tuần này', 'tuần tới'])}"
    return f"{random.randint(1,30)} ngày nữa"

QUERY_TEMPLATES = {
    "find_tour_with_location": [
        "Tôi muốn đi tour {location}",
        "Cho tôi thông tin tour {location}",
        "Có tour nào ở {location} không?",
        "Tìm tour {location} cho tôi",
        "Tour du lịch {location} nào đang có?",
        "Tôi cần tour ở {location}",
        "Gợi ý tour đi {location} được không?",
        "{location} có tour gì hay không?",
        "Tour {location} nào phù hợp cho gia đình?",
        "Tôi muốn khám phá {location} qua tour",
        "Tour {location} cho người lớn tuổi có không?",
        "Có tour nào ở {location} dịp lễ không?",
        "Tìm tour {location} cho nhóm bạn đi!"
    ],
    "find_tour_with_location_and_time": [
        "Tôi muốn tour {location} {time}",
        "Tour {location} khởi hành {time} có không?",
        "Tìm tour {location} vào {time}",
        "Có tour nào đi {location} {time} không?",
        "{location} {time} có tour gì hay?",
        "Tour {location} dịp {time} thế nào?",
        "Tôi cần tour {location} vào {time}",
        "Gợi ý tour {location} khởi hành {time}",
        "Tour {location} tháng {time} giá bao nhiêu?",
        "Tôi muốn đi {location} và {location2} vào {time}",
        "Tour {location} {time} cho cặp đôi có không?",
        "Có tour nào ở {location} vào {time} giá rẻ không?"
    ],
    "find_tour_with_location_and_price": [
        "Tour {location} giá {price} có không?",
        "Tìm tour {location} {price}",
        "Tôi muốn tour {location} {price}",
        "Có tour {location} nào {price} không?",
        "{location} {price} có tour gì hay?",
        "Tour {location} dưới {price} có không?",
        "Gợi ý tour {location} giá khoảng {price}",
        "Tôi cần tour {location} với ngân sách {price}",
        "Tour {location} giá rẻ {price} thế nào?",
        "Tour {location} và {location2} giá {price} có không?",
        "Tour {location} {price} có bao gồm ăn uống không?",
        "Có tour nào {location} {price} cho nhóm bạn không?"
    ],
    "find_tour_with_price": [
        "Tìm tour giá {price} có không?",
        "Có tour nào giá {price} không?",
        "Gợi ý tour khoảng {price}",
        "Tour nào dưới {price} vậy?",
        "Tôi muốn tour giá {price}",
        "Tour giá rẻ {price} có gì hay?",
        "Có tour nào ngân sách {price} không?",
        "Tìm tour giá {price} cho gia đình",
        "Tour {price} có bao gồm vé máy bay không?",
        "Gợi ý tour giá {price} cho cặp đôi",
        "Tour nào giá {price} đi được nhiều nơi?"
    ],
    "find_tour_with_time": [
        "Tìm tour khởi hành {time} có không?",
        "Có tour nào đi {time} không?",
        "Tour nào khởi hành vào {time} vậy?",
        "Gợi ý tour đi vào {time}",
        "Tôi muốn tour khởi hành {time}",
        "Tour {time} có gì hay ho?",
        "Có tour nào vào {time} giá rẻ không?",
        "Tìm tour đi vào {time} cho nhóm bạn",
        "Tour khởi hành {time} đi đâu đẹp?",
        "Tour nào vào {time} phù hợp gia đình?"
    ],
    "find_tour_with_time_and_price": [
        "Tìm tour {time} giá {price} có không?",
        "Có tour nào {time} giá {price} không?",
        "Tour {time} dưới {price} có gì hay?",
        "Gợi ý tour {time} giá khoảng {price}",
        "Tôi muốn tour {time} ngân sách {price}",
        "Tour {time} giá {price} đi đâu đẹp?",
        "Có tour nào {time} {price} cho cặp đôi không?",
        "Tìm tour khởi hành {time} giá {price}",
        "Tour {time} giá rẻ {price} thế nào?",
        "Tour {time} {price} có bao gồm ăn uống không?"
    ],
    "find_with_all": [
        "Tìm tour {location} {time} giá {price} có không?",
        "Có tour {location} vào {time} giá {price} không?",
        "Tour {location} {time} dưới {price} có gì hay?",
        "Gợi ý tour {location} {time} giá khoảng {price}",
        "Tôi muốn tour {location} {time} ngân sách {price}",
        "Tour {location} {time} giá {price} đi đâu đẹp?",
        "Có tour {location} {time} {price} cho gia đình không?",
        "Tìm tour {location} khởi hành {time} giá {price}",
        "Tour {location} {time} giá rẻ {price} thế nào?",
        "Tour {location} và {location2} {time} giá {price} có không?",
        "Tour {location} {time} {price} có bao gồm vé máy bay không?"
    ]
}

# ───────────────────────────── Rate-limit ───────────────────────────────
RPM_LIMIT = 300  # requests per minute – chỉnh theo quota của bạn

@sleep_and_retry
@limits(calls=RPM_LIMIT, period=60)
def call_api(prompt: str) -> str:
    """Gửi prompt tới Gemini với rate-limit và trả về text."""
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp.text else ""
    except Exception as exc:
        logger.warning("Lỗi khi gọi API: %s", exc)
        return ""  # trả về rỗng, caller sẽ dùng fallback

def extract_questions_from_response(response: str) -> List[str]:
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return [str(item) if isinstance(item, str) else item.get("question", "")
                    for item in data if isinstance(item, str) or "question" in item]
    except json.JSONDecodeError:
        pass
    questions = [q for q in re.findall(r'"([^"]+)"', response) if len(q) > 5]
    # Loại bỏ câu hỏi kết thúc bằng "với?" hoặc không hợp lệ
    return [q for q in questions if not q.endswith("với?") and q.strip()[-1] in ".!?"]

# ─────────────────────── Sinh dữ liệu intent ────────────────────────────
def generate_intent_data(num_samples: Dict[str, int],
                         use_api: bool = True) -> List[Dict]:
    intent_data: List[Dict[str, str]] = []
    seen: set[str] = set()

    for intent, target in num_samples.items():
        logger.info("Sinh dữ liệu intent %-35s ( %d )", intent, target)
        templates = QUERY_TEMPLATES[intent]
        used_locations = set()
        while sum(1 for d in intent_data if d["intent"] == intent) < target:
            region = random.choice(list(GROUPS))
            location = random.choice(GROUPS[region])
            location2 = random.choice(GROUPS[region]) if random.random() < 0.3 else ""
            available_locations = [loc for loc in GROUPS[region] if loc not in used_locations]
            if not available_locations:
                used_locations.clear()  # Reset nếu đã dùng hết
                available_locations = GROUPS[region]
            location = random.choice(available_locations)
            used_locations.add(location)
            time_expr = random_time_expression() \
                if intent in ["find_tour_with_location_and_time", "find_tour_with_time", 
                              "find_tour_with_time_and_price", "find_with_all"] else ""
            price_expr = random_money_expression() \
                if intent in ["find_tour_with_location_and_price", "find_tour_with_price", 
                              "find_tour_with_time_and_price", "find_with_all"] else ""

            # sinh câu cơ bản từ template
            base_query = random.choice(templates).format(
                location=location, location2=location2,
                time=time_expr, price=price_expr
            )

            # 20 % câu cụt
            if random.random() < 0.2:
                if intent == "find_tour_with_location":
                    base_query = f"{location} có tour không?"
                elif intent == "find_tour_with_location_and_time":
                    base_query = f"{location} {time_expr} tour nào?"
                elif intent == "find_tour_with_location_and_price":
                    base_query = f"{location} {price_expr} tour gì?"
                elif intent == "find_tour_with_price":
                    base_query = f"Tour {price_expr} có gì?"
                elif intent == "find_tour_with_time":
                    base_query = f"Tour {time_expr} nào hay?"
                elif intent == "find_tour_with_time_and_price":
                    base_query = f"Tour {time_expr} {price_expr} có không?"
                elif intent == "find_with_all":
                    base_query = f"{location} {time_expr} {price_expr} tour nào?"

            if base_query in seen:
                continue
            seen.add(base_query)

            # --- gọi API để paraphrase thành 5 câu khác (nếu bật) -------------
            if use_api:
                prompt = f"""
                        Bạn là khách hàng trên chatbot du lịch.
                        Bạn sẽ hỏi nhưng câu khác nhau về tour du lịch.
                        Yêu cầu:
                        - Sinh câu hỏi có nội dung phù hợp với thực thể trong intent:
                        -- Chỉ location: tập trung vào việc mong muốn đề xuất tour (Không cần quá rườm rà tập trung vào việc hỏi tour).
                        -- Chỉ time: tập trung vào việc đưa ra thời gian khởi hành mong muốn .
                        -- Chỉ price: tập trung vào việc muốn chọn tour trong ngân sách đó.
                        -- location + time: tập trung vào việc muốn được đề xuất tour khởi hành vào thời gian đó và địa điểm đó (vd: Tôi muốn tìm tour đi Đà Lạt vào tháng bảy).
                        -- location + price: tập trung vào việc muốn chọn tour trong ngân sách đó và địa điểm đó.
                        -- time + price: Phần này chia làm 2 trường hợp: 
                        ---Trường hợp 1: Khách hàng đà từng nhắc đến 1 địa điểm trước đó và bây giờ bạn chỉ cần cung cấp thời gian và giá cả.
                        ---Trường hợp 2: Khách hàng không nhắc đến địa điểm nào trước đó và bây giờ bạn cần hỏi để đối phương đề xuất tour với địa điểm 1 cách đại khái(đi biển, lên núi, vào rừng) hoặc không và có 2 thứ bắt buộc có là thời gian và giá cả.
                        -- location + time + price: tập trung vào việc muốn chọn tour ở địa diểm đó khởi hành vào thời gian đó trong ngân sách đó.
                        Viết 5 câu hỏi tiếng Việt (5–15 từ)
                        thuộc intent "{intent}". Phải chứa:
                        {f"- Địa điểm: {location}{f' và {location2}' if location2 else ''}" 
                         if intent in ["find_tour_with_location", "find_tour_with_location_and_time", 
                                       "find_tour_with_location_and_price", "find_with_all"] else ""}
                        {f"- Thời gian: {time_expr}" if time_expr else ""}
                        {f"- Giá tiền: {price_expr}" if price_expr else ""}
                        Dạng thoại tự nhiên, có thể khẩu ngữ.
                        Trả về MẢNG JSON các chuỗi, ví dụ:
                        ["Câu 1", "Câu 2", "Câu 3", "Câu 4", "Câu 5"]
                        """
                resp_text = call_api(prompt)
                questions = extract_questions_from_response(resp_text)
                for q in questions:
                    if q and q not in seen:
                        intent_data.append({"query": q, "intent": intent})
                        seen.add(q)
                        if sum(1 for d in intent_data if d["intent"] == intent) >= target:
                            break
                else:
                    # nếu API fail – dùng bản gốc
                    intent_data.append({"query": base_query, "intent": intent})
            else:
                intent_data.append({"query": base_query, "intent": intent})

    return intent_data

# ───────────────────────── Lưu file JSON ───────────────────────────────
def save_intent_data(data: List[Dict], output_path: str) -> None:
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Đã lưu %d mẫu → %s", len(data), output_path)
    except Exception as exc:
        logger.error("Lỗi khi lưu file: %s", exc)
        raise

# ───────────────────────────── Main ─────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh dataset intent cho chatbot du lịch")
    parser.add_argument("--output", default="extended_intent_train_data_v2.json",
                        help="File JSON đầu ra")
    parser.add_argument("--use-api", action="store_true",
                        help="Bật gọi Gemini để paraphrase (tốn quota)")
    args = parser.parse_args()

    NUM_SAMPLES = {
        "find_tour_with_location":             700,
        "find_tour_with_location_and_time":    700,
        "find_tour_with_location_and_price":   700,
        "find_tour_with_price":                700,
        "find_tour_with_time":                 700,
        "find_tour_with_time_and_price":       1200,
        "find_with_all":                       1700
    }
    # NUM_SAMPLES = {
    #     "find_tour_with_location":             30,
    #     "find_tour_with_location_and_time":    30,
    #     "find_tour_with_location_and_price":   30,
    #     "find_tour_with_price":                30,
    #     "find_tour_with_time":                 30,
    #     "find_tour_with_time_and_price":       30,
    #     "find_with_all":                       30,
    # }

    try:
        data = generate_intent_data(NUM_SAMPLES, use_api=args.use_api)
        save_intent_data(data, args.output)

        logger.info("Ví dụ 5 câu đầu:")
        for i, sample in enumerate(data[:5], 1):
            logger.info("  %d) %s", i, sample)
    except Exception as exc:
        logger.error("Lỗi thực thi: %s", exc)
        raise