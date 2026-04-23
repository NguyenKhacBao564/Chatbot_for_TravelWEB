import os
import json
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
import re
from jsonschema import validate, ValidationError

# Load schema để kiểm tra dữ liệu
SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 5, "maxLength": 300},
        "answer": {"type": "string", "minLength": 5, "maxLength": 500},
        "tags": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["question", "answer", "tags"],
    "additionalProperties": False
}

load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Danh sách các chủ đề chung
GENERAL_TOPICS = [
    {"tag": "tour_booking_conditions", "name": "Điều kiện đặt tour"},
    {"tag": "tour_cancellation_refund", "name": "Hủy tour và chính sách hoàn tiền"},
    {"tag": "tour_schedule_changes", "name": "Thay đổi lịch trình tour"},
    {"tag": "tour_customer_support", "name": "Hỗ trợ khách hàng trong tour"}
]

# Prompt mẫu để generate Q&A chung
PROMPT_TEMPLATE = """
Bạn là một chuyên gia du lịch, hỗ trợ người dùng qua chatbot tiếng Việt.  
Tôi cần bạn tạo dữ liệu Q&A để huấn luyện chatbot tư vấn du lịch.  
Hãy tạo **10-20 cặp câu hỏi và câu trả lời** về chủ đề: “{topic_name}”.  
**Yêu cầu:**  
- Câu hỏi và câu trả lời phải bằng **tiếng Việt**, ngắn gọn, tự nhiên, và thân thiện như chatbot trả lời người dùng.  
- Câu hỏi dài 1-2 câu, không quá 300 ký tự.  
- Tránh lặp lại nội dung giữa các cặp Q&A.  
- Đáp ứng định dạng JSON: [{{"question": "...", "answer": "..."}}].  
- Câu trả lời dài 2-3 câu, không quá 500 ký tự, phải cung cấp thông tin chi tiết, hữu ích và có chiều sâu (ví dụ: thêm mẹo, số liệu cụ thể, hoặc gợi ý thực tế).  
- Không đề cập đến bất kỳ địa điểm, tỉnh/thành phố cụ thể nào trong câu hỏi và câu trả lời.  
- Ví dụ: [{{"question": "Trẻ em bao nhiêu tuổi thì được đặt tour?", "answer": "Trẻ em dưới 18 tuổi cần đi cùng người lớn để đặt tour. Bạn cần mang theo giấy khai sinh để xác nhận độ tuổi. Một số tour có thể yêu cầu bảo hiểm du lịch."}}]
"""

class GeminiClient:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"response_mime_type": "application/json"}
        )

    async def generate_faq(self, topic_name, retries=3):
        prompt = PROMPT_TEMPLATE.format(topic_name=topic_name)
        for attempt in range(1, retries + 1):
            try:
                response = await self.model.generate_content_async(
                    contents=prompt,
                    generation_config={"temperature": 0.5, "max_output_tokens": 4000}
                )
                text = response.text
                try:
                    data = json.loads(text)
                    return data
                except json.JSONDecodeError:
                    m = re.search(r"\[.*\]", text, re.DOTALL)
                    if m:
                        return json.loads(m.group(0))
                    raise ValueError("Invalid JSON format in response")
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "quota" in error_msg or "server error" in error_msg:
                    if attempt < retries:
                        print(f"Attempt {attempt} failed: {error_msg}. Retrying after {attempt} seconds...")
                        await asyncio.sleep(attempt)
                        continue
                print(f"Error generating FAQ for {topic_name}: {error_msg}")
                return []
        print(f"Max retries reached for {topic_name}. Skipping...")
        return []

def validate_qa_pairs(qa_pairs, start_id):
    """Kiểm tra và lọc các cặp Q&A hợp lệ, gán ID duy nhất"""
    valid_pairs = []
    seen = set()  # Để kiểm tra trùng lặp câu hỏi
    current_id = start_id

    for qa in qa_pairs:
        qa_copy = qa.copy()
        qa_copy["tags"] = []  # Tạm thêm tags để validate
        try:
            validate(qa_copy, SCHEMA)
            question = qa["question"]
            if question in seen:
                print(f"Duplicate question skipped: {question}")
                continue
            if len(qa["question"]) > 5 and len(qa["answer"]) > 5:  # Tránh rỗng hoặc quá ngắn
                seen.add(question)
                qa["id"] = current_id
                valid_pairs.append(qa)
                current_id += 1
        except ValidationError as ve:
            print(f"Invalid QA pair skipped: {qa}. Error: {ve.message}")
            continue
    return valid_pairs, current_id

async def main():
    client = GeminiClient()
    all_faq = []
    start_id = 0

    # Đọc start_id từ file (nếu có) để tiếp tục từ ID cuối cùng
    start_id_file = "data/raw/last_id_general.txt"
    if os.path.exists(start_id_file):
        with open(start_id_file, "r") as f:
            start_id = int(f.read().strip())

    for topic in GENERAL_TOPICS:
        print(f"Generating FAQ for topic: {topic['name']}")
        qa_pairs = await client.generate_faq(topic["name"])
        valid_pairs, start_id = validate_qa_pairs(qa_pairs, start_id)
        for qa in valid_pairs:
            qa["tags"] = [topic["tag"]]
        all_faq.extend(valid_pairs)
        print(f"Generated {len(valid_pairs)} valid Q&A for {topic['name']}")

    # Lưu start_id cuối cùng
    with open(start_id_file, "w") as f:
        f.write(str(start_id))

    # Lưu ra file
    output_file = "data/raw/faq_general.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_faq, f, ensure_ascii=False, indent=2)
    print(f"Đã tạo {len(all_faq)} mục Q&A vào {output_file}")

if __name__ == "__main__":
    asyncio.run(main())