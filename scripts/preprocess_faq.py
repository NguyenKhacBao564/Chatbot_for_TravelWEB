# # preprocess_faq.py
# import json
# import re
# import unicodedata
# import sys
# from pathlib import Path
# from jsonschema import validate, ValidationError
# import argparse

# VALID_CATEGORIES = {
#        "destination", "weather", "transport", "scenery",
#        "visa", "tour", "payment", "career", "company", "membership", "promotion",
#        "destination_basics", "weather_best_time", "scenery_things_to_do", "visa_entry",
#        "tour_booking", "pricing_payment_currency", "promotions_membership",
#        "accommodation", "food_dining", "health_safety_insurance", "culture_etiquette",
#        "events_festivals", "connectivity_sim_wifi", "budgeting_tips",
#        "accessibility_family", "solo_female_safety", "sustainability_eco",
#        "emergency_laws", "packing_checklist",
#        "famous destination", "clothing", "shopping", "entertainment",
#        "tour_booking_conditions", "tour_cancellation_refund", "tour_schedule_changes", "tour_customer_support",
#        "food", "service", "culture"  # Thêm các category bị thiếu
#    }

# SCHEMA_PATH = Path("data/schema_faq.jsonschema")

# def normalize_text(text: str) -> str:
#     """Chuẩn hóa văn bản: chuẩn hóa unicode, xóa HTML tags, ký tự đặc biệt, và khoảng trắng thừa."""
#     text = unicodedata.normalize("NFKC", text)
#     text = re.sub(r"<[^>]+>", "", text)  # Xóa HTML tags
#     text = re.sub(r"[^\w\s.,!?-]", "", text)  # Xóa ký tự không cần thiết
#     return " ".join(text.split()).strip()

# def load_schema():
#     """Tải schema từ file."""
#     try:
#         return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
#     except Exception as e:
#         sys.exit(f"[ERROR] Cannot load schema from {SCHEMA_PATH}: {e}")

# def validate_and_clean(input_file, output_file):
#     """Làm sạch và chuẩn hóa dữ liệu FAQ."""
#     schema = load_schema()
    
#     # Đọc dữ liệu đầu vào
#     try:
#         raw = json.loads(Path(input_file).read_text(encoding="utf-8"))
#     except Exception as e:
#         sys.exit(f"[ERROR] Cannot read {input_file}: {e}")

#     cleaned = []
#     seen = set()  # Để kiểm tra trùng lặp câu hỏi và câu trả lời

#     for entry in raw:
#         # 1. Kiểm tra các trường bắt buộc
#         if not all(k in entry for k in ("id", "question", "answer")):
#             print(f"❌ Missing required field (id, question, answer) → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             continue

#         # 2. Chuẩn hóa văn bản
#         entry["question"] = normalize_text(entry["question"])
#         entry["answer"] = normalize_text(entry["answer"])

#         # 2.1. Kiểm tra nội dung rỗng sau khi chuẩn hóa
#         if not entry["question"] or not entry["answer"]:
#             print(f"❌ Empty question or answer after normalization → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             continue

#         # 3. Kiểm tra độ dài câu hỏi và câu trả lời
#         if len(entry["question"]) < 5 or len(entry["answer"]) < 5:
#             print(f"❌ Question or answer too short → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             continue

#         # 4. Kiểm tra trùng lặp
#         qa_pair = (entry["question"], entry["answer"])
#         if qa_pair in seen:
#             print(f"❌ Duplicate question-answer pair → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             continue
#         seen.add(qa_pair)

#         # 5. Xử lý trường location
#         if "location" not in entry:
#             entry["location"] = "General"

#         # 6. Đồng bộ category và tags
#         if "category" in entry and entry["category"]:
#             if entry["category"] not in VALID_CATEGORIES:
#                 print(f"❌ Invalid category '{entry['category']}' → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#                 continue
#             # Thêm category vào tags nếu chưa có
#             if "tags" not in entry or not entry["tags"]:
#                 entry["tags"] = [entry["category"]]
#             elif entry["category"] not in entry["tags"]:
#                 entry["tags"].append(entry["category"])
#         else:
#             # Nếu không có category, lấy từ tags[0] nếu có
#             if "tags" in entry and entry["tags"]:
#                 entry["category"] = entry["tags"][0] if entry["tags"][0] in VALID_CATEGORIES else None
#             else:
#                 print(f"❌ Missing category and tags → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#                 continue

#         # 7. Kiểm tra tags
#         if not entry.get("tags"):
#             print(f"⚠️ Missing tags, assigned default tag 'general': id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             entry["tags"] = ["general"]
#         # Loại bỏ tags không hợp lệ
#         entry["tags"] = [tag for tag in entry["tags"] if tag in schema["properties"]["tags"]["items"]["enum"]]
#         if not entry["tags"]:
#             print(f"❌ No valid tags after filtering → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}")
#             continue

#         # 8. Xử lý sub_details và priority (tùy chọn, không bắt buộc)
#         if "sub_details" not in entry or not isinstance(entry["sub_details"], dict):
#             entry["sub_details"] = {"season": None, "suitable_for": None, "additional_info": "Không có thông tin bổ sung."}
#         else:
#             sub_details = entry["sub_details"]
#             sub_details.setdefault("season", None)
#             sub_details.setdefault("suitable_for", None)
#             sub_details.setdefault("additional_info", "Không có thông tin bổ sung.")
#         if "priority" not in entry:
#             entry.pop("priority", None)  # Xóa nếu không có

#         # 9. Validate theo schema
#         try:
#             validate(entry, schema)
#             cleaned.append(entry)
#         except ValidationError as ve:
#             print(f"❌ Schema violation → skip: id={entry.get('id', 'N/A')}, location={entry.get('location', 'N/A')}, question={entry.get('question', 'N/A')}, error={ve.message}")
#             continue

#     # Lưu dữ liệu đã làm sạch
#     output_path = Path(output_file)
#     output_path.parent.mkdir(parents=True, exist_ok=True)
#     output_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
#     print(f"✅ Saved {len(cleaned)} valid entries → {output_file}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Preprocess FAQ data.")
#     parser.add_argument("--input", required=True, help="Input JSON file path")
#     parser.add_argument("--output", required=True, help="Output JSON file path")
#     args = parser.parse_args()

#     validate_and_clean(args.input, args.output)

import json
import re
from collections import Counter

def clean_text(text):
    """Làm sạch văn bản."""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Loại bỏ khoảng trắng thừa
    text = text.replace("tron", "trong")  # Sửa lỗi chính tả
    return text

def normalize_intent(intent):
    """Chuẩn hóa intent."""
    intent_mapping = {
        "find_tour_with_price": "find_tour_with_location_and_price",
        "find_tour_with_time": "find_tour_with_location_and_time",
        "find_tour_with_time_and_price": "find_tour_with_location_and_time",
        "find_with_all": "find_tour_with_location_and_time",
        "find_tour_with_location": "find_tour_with_location",
        "find_tour_with_location_and_time": "find_tour_with_location_and_time",
        "find_tour_with_location_and_price": "find_tour_with_location_and_price",
        "out_of_scope": "out_of_scope"
    }
    return intent_mapping.get(intent, "out_of_scope")

def process_dataset(input_file, output_file):
    """Xử lý dataset: làm sạch, chuẩn hóa, thêm nhãn."""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    label_mapping = {
        "find_tour_with_location": 0,
        "find_tour_with_location_and_time": 1,
        "find_tour_with_location_and_price": 2,
        "out_of_scope": 3
    }

    processed_data = []
    for item in data:
        query = clean_text(item["query"])
        intent = normalize_intent(item["intent"])
        label = label_mapping.get(intent, 3)  # Mặc định là out_of_scope nếu không khớp

        if query and len(query) >= 5:  # Bỏ qua query rỗng hoặc quá ngắn
            processed_data.append({
                "query": query,
                "intent": intent,
                # "label": label
            })

    # Kiểm tra phân bố intent
    intent_counts = Counter(item["intent"] for item in processed_data)
    print("Phân bố intent:", intent_counts)

    # Lưu dữ liệu đã xử lý
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"Đã xử lý {len(processed_data)} mẫu vào {output_file}")

if __name__ == "__main__":
    input_file = "data/processed/merged_intent_data.json"
    output_file = "data/processed/processed_intent_data.json"
    process_dataset(input_file, output_file)