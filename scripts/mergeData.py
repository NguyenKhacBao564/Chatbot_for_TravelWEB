# import json
# from pathlib import Path

# # files = [
# #     "faq_group1_cleaned.json", "faq_group2_cleaned.json", "faq_group3_cleaned.json", 
# #     "faq_group4_cleaned.json", "faq_manual_cleaned.json"
# # ]
# files = [
#     "faq_north.json", "faq_central.json", "faq_south.json"
# ]
# combined_data = []

# for file in files:
#     # path = Path(f"data/processed/{file}")
#     path = Path(f"data/raw/{file}")
#     data = json.loads(path.read_text(encoding="utf-8"))
#     combined_data.extend(data)

# # output_path = Path("data/processed/faq_combined.json")
# output_path = Path("data/raw/faq_combined_ncs.json")
# output_path.write_text(json.dumps(combined_data, ensure_ascii=False, indent=2), encoding="utf-8")
# print(f"Đã gộp {len(combined_data)} mục vào {output_path}")

# import json
# from pathlib import Path

# files = ["faqupdate_north.json", "faqupdate_central.json", "faqupdate_south.json", "faq_general.json"]
# combined_data = []
# current_id = 0

# for file in files:
#     path = Path(f"data/raw/{file}")
#     data = json.loads(path.read_text(encoding="utf-8"))
#     for item in data:
#         item["id"] = current_id
#         if "location" not in item:
#             item["location"] = "General"
#         combined_data.append(item)
#         current_id += 1

# output_path = Path("data/raw/faq_combined.json")
# output_path.write_text(json.dumps(combined_data, ensure_ascii=False, indent=2), encoding="utf-8")
# print(f"Đã gộp {len(combined_data)} mục vào {output_path}")

import json
import os

def load_json_file(file_path):
    """Đọc file JSON và trả về danh sách dữ liệu."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file {file_path}: {e}")
        return []

def merge_datasets(input_files, output_file):
    """Ghép các dataset từ nhiều file JSON."""
    merged_data = []
    seen_queries = set()  # Để kiểm tra trùng lặp

    for file_path in input_files:
        data = load_json_file(file_path)
        for item in data:
            query = item["query"]
            if query not in seen_queries:  # Bỏ qua nếu trùng
                merged_data.append(item)
                seen_queries.add(query)
            else:
                print(f"Trùng lặp query: {query}")

    # Lưu dữ liệu ghép vào file mới
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    print(f"Đã ghép {len(merged_data)} mẫu vào {output_file}")

if __name__ == "__main__":
    input_files = [
        "data/raw/extended_intent_train_data_v2.json",  # File chứa 46 mẫu tour du lịch
        "data/raw/out_of_scope_intent_data.json",  # File chứa 300 mẫu out_of_scope
        # Thêm các file JSON khác nếu có, ví dụ: "data/raw/faq_general.json"
    ]
    output_file = "data/processed/merged_intent_data.json"
    merge_datasets(input_files, output_file)