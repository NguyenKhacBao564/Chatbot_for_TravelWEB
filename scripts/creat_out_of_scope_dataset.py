#!/usr/bin/env python
# coding: utf-8
"""
create_out_of_scope_dataset.py – Sinh bộ dữ liệu intent out_of_scope cho chatbot du lịch
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
    "north": [
        "Hà Nội", "Hải Phòng", "Bắc Giang", "Bắc Kạn", "Cao Bằng", "Hà Giang", "Lạng Sơn", "Phú Thọ",
        "Quảng Ninh", "Thái Nguyên", "Tuyên Quang", "Lào Cai", "Yên Bái", "Điện Biên", "Hòa Bình",
        "Lai Châu", "Sơn La", "Bắc Ninh", "Hà Nam", "Hải Dương", "Hưng Yên", "Thái Bình",
        "Nam Định", "Ninh Bình", "Vĩnh Phúc"
    ],
    "central": [
        "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị", "Thừa Thiên Huế", "Đà Nẵng",
        "Quảng Nam", "Quảng Ngãi", "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận"
    ],
    "south": [
        "TP Hồ Chí Minh", "Cần Thơ", "An Giang", "Bạc Liêu", "Bến Tre", "Cà Mau", "Đồng Tháp", "Hậu Giang",
        "Kiên Giang", "Long An", "Sóc Trăng", "Tiền Giang", "Trà Vinh", "Vĩnh Long", "Bà Rịa–Vũng Tàu",
        "Bình Dương", "Bình Phước", "Đồng Nai", "Tây Ninh", "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông",
        "Lâm Đồng"
    ]
}

# Danh sách chủ đề thay thế cho TOPICS
THEMES = ["education", "gaming", "science", "entertainment"]

# Mẫu câu hỏi out_of_scope
OUT_OF_SCOPE_TEMPLATES = [
    # Chung
    "Làm thế nào để {action} ở {location}?",
    "Bạn biết gì về {theme} ở {location}?",
    "Hãy kể tôi nghe về {theme}?",
    "Có ai nổi tiếng về {theme} ở {location} không?",
    "{theme} ở {location} có gì đặc biệt?",
    # Giáo dục
    "Làm sao để thi đậu đại học {location}?",
    "Trường đại học nào ở {location} tốt nhất?",
    "Cách học {subject} hiệu quả là gì?",
    # Giải trí
    "Cách chơi game {game} là gì?",
    "Ca sĩ nổi tiếng nhất ở {location} là ai?",
    "Bộ phim {genre} nào đang hot ở {location}?",
    # Khoa học
    "Số {math_term} có ý nghĩa gì?",
    "Tại sao {science_fact} lại xảy ra?",
    # Khác
    "Thời gian bay từ {location} đến {foreign_city} là bao lâu?",
    "Hôm nay {location} có gì vui không?",
    "Bí mật về {theme} là gì?"
]

# Danh sách bổ sung để điền vào template
ACTIONS = ["nấu món ăn ngon", "học lập trình", "chụp ảnh đẹp", "kiếm tiền online"]
SUBJECTS = ["toán", "văn", "lý", "hóa", "tiếng Anh"]
GAMES = ["Liên Quân Mobile", "PUBG", "Free Fire", "Minecraft"]
GENRES = ["hành động", "tình cảm", "kinh dị", "hài"]
MATH_TERMS = ["pi", "e", "số nguyên tố", "Fibonacci"]
SCIENCE_FACTS = ["mưa", "sấm sét", "cầu vồng", "động đất"]
FOREIGN_CITIES = ["Tokyo", "Paris", "New York", "London", "Sydney"]

# ───────────────────────────── Rate-limit ───────────────────────────────
RPM_LIMIT = 60  # requests per minute

@sleep_and_retry
@limits(calls=RPM_LIMIT, period=60)
def call_api(prompt: str) -> str:
    """Gửi prompt tới Gemini với rate-limit và trả về text."""
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        logger.warning("Lỗi khi gọi API: %s", e)
        return ""

def extract_questions_from_response(response: str) -> List[str]:
    """Trích xuất câu hỏi từ phản hồi API (JSON hoặc plain)."""
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return [str(item) if isinstance(item, str) else item.get("question", "")
                    for item in data]
    except json.JSONDecodeError:
        return [q for q in re.findall(r'"([^"]+)"', response) if len(q) > 5]
    return []

# ─────────────────────── Sinh dữ liệu intent ────────────────────────────
def generate_out_of_scope_data(num_samples: int, use_api: bool = True) -> List[Dict]:
    intent_data: List[Dict[str, str]] = []
    seen: set[str] = set()
    intent = "out_of_scope"

    logger.info("Sinh dữ liệu intent %s ( %d )", intent, num_samples)

    while len(intent_data) < num_samples:
        # Chọn ngẫu nhiên các thành phần
        location = random.choice(GROUPS[random.choice(["north", "central", "south"])]) \
            if random.random() < 0.5 else ""  # 50% cơ hội có địa điểm
        theme = random.choice(THEMES)  # Sử dụng THEMES thay vì TOPICS
        action = random.choice(ACTIONS)
        subject = random.choice(SUBJECTS)
        game = random.choice(GAMES)
        genre = random.choice(GENRES)
        math_term = random.choice(MATH_TERMS)
        science_fact = random.choice(SCIENCE_FACTS)
        foreign_city = random.choice(FOREIGN_CITIES)

        # Chọn mẫu ngẫu nhiên
        template = random.choice(OUT_OF_SCOPE_TEMPLATES)
        try:
            base_query = template.format(
                location=location, theme=theme, action=action, subject=subject,
                game=game, genre=genre, math_term=math_term, science_fact=science_fact,
                foreign_city=foreign_city
            )
        except KeyError:
            # Nếu template không khớp, chọn template khác
            continue

        # 30% cơ hội tạo câu cụt
        if random.random() < 0.3:
            if theme in ["education", "science"]:
                base_query = f"{subject.capitalize()} học thế nào?" if theme == "education" else f"{math_term} là gì?"
            elif theme == "gaming":
                base_query = f"Chơi {game} sao cho giỏi?"
            elif theme == "entertainment":
                base_query = f"Phim {genre} nào hot?"
            else:
                base_query = f"{theme} ở {location} thế nào?" if location else f"{theme} là gì?"

        if base_query in seen:
            continue
        seen.add(base_query)

        # Gọi API để paraphrase (nếu bật)
        if use_api:
            prompt = f"""
Bạn là người dùng chatbot du lịch, nhưng đặt câu hỏi KHÔNG liên quan đến du lịch.
Viết 5 câu hỏi tiếng Việt (5–15 từ) thuộc intent "out_of_scope".
Câu hỏi phải tự nhiên, có thể khẩu ngữ, và liên quan đến chủ đề "{theme}".
{f"Nếu phù hợp, đề cập đến địa điểm: {location}" if location else ""}
Ví dụ: "Làm sao để thi đậu đại học ở Hà Nội?"
Trả về MẢNG JSON các chuỗi, ví dụ:
["Câu 1", "Câu 2", "Câu 3", "Câu 4", "Câu 5"]
"""
            resp_text = call_api(prompt)
            questions = extract_questions_from_response(resp_text)
            for q in questions:
                if q and q not in seen:
                    intent_data.append({"query": q, "intent": intent})
                    seen.add(q)
                    if len(intent_data) >= num_samples:
                        break
            else:
                # Nếu API thất bại, dùng câu gốc
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
    except Exception as e:
        logger.error("Lỗi khi lưu file: %s", e)
        raise

# ───────────────────────────── Main ─────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh dataset intent out_of_scope cho chatbot du lịch")
    parser.add_argument("--output", default="out_of_scope_intent_data.json",
                        help="File JSON đầu ra")
    parser.add_argument("--num-samples", type=int, default=100,
                        help="Số lượng mẫu dữ liệu cần sinh")
    parser.add_argument("--use-api", action="store_true",
                        help="Bật gọi Gemini để paraphrase (tốn quota)")
    args = parser.parse_args()

    try:
        data = generate_out_of_scope_data(args.num_samples, use_api=args.use_api)
        save_intent_data(data, args.output)

        logger.info("Ví dụ 5 câu đầu:")
        for i, sample in enumerate(data[:5], 1):
            logger.info("  %d) %s", i, sample)
    except Exception as e:
        logger.error("Lỗi thực thi: %s", e)
        raise