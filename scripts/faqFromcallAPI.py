import os
import json
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
import re
from jsonschema import validate, ValidationError
import logging
import argparse

# Thiết lập logging
logging.basicConfig(filename='faq_generation.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Schema để kiểm tra dữ liệu
SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "location": {"type": "string"},
        "category": {"type": "string", "enum": ["weather", "culture", "payment", "transport", "food", "service", "famous destination", "clothing", "shopping", "entertainment"]},
        "question": {"type": "string", "minLength": 5, "maxLength": 300},
        "answer": {"type": "string", "minLength": 5, "maxLength": 500},
        "sub_details": {
            "type": "object",
            "properties": {
                "season": {"type": ["string", "null"]},
                "suitable_for": {"type": ["string", "null"]},
                "additional_info": {"type": ["string", "null"]}
            },
            "required": ["season", "suitable_for", "additional_info"]
        },
        "priority": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["id", "location", "category", "question", "answer", "sub_details", "priority", "tags"],
    "additionalProperties": False
}

load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Nhóm vùng và danh sách tỉnh/thành
GROUPS = {
    "north": [
        "Hà Nội", "Hải Phòng", "Bắc Giang", "Bắc Kạn", "Cao Bằng", "Hà Giang", "Lạng Sơn", "Phú Thọ", 
        "Quảng Ninh", "Thái Nguyên", "Tuyên Quang", "Lào Cai", "Yên Bái", "Điện Biên", "Hòa Bình", 
        "Lai Châu", "Sơn La", "Bắc Ninh", "Hà Nam", "Hải Dương", "Hưng Yên", "Thái Bình", 
        "Nam Định", "Ninh Bình", "Vĩnh Phúc"
    ],
    "central": [
        "Thanh Hóa", "Nghệ An", "Hà Tĩnh",  "Quảng Bình", "Quảng Trị", "Thừa Thiên Huế", "Đà Nẵng", 
        "Quảng Nam", "Quảng Ngãi", "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận"
    ],
    "south": [
        "TP Hồ Chí Minh", "Cần Thơ", "An Giang", "Bạc Liêu", "Bến Tre", "Cà Mau", "Đồng Tháp", "Hậu Giang", 
        "Kiên Giang", "Long An", "Sóc Trăng", "Tiền Giang", "Trà Vinh", "Vĩnh Long", "Bà Rịa–Vũng Tàu", 
        "Bình Dương", "Bình Phước", "Đồng Nai", "Tây Ninh", "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông", 
        "Lâm Đồng"
    ]
}

# GROUPS = {
#     "north": [
#         "Hà Nội", "Cao Bằng", "Quảng Ninh"
#     ],
#     "central": [
#         "Thanh Hóa", "Nghệ An", "Hà Tĩnh",  "Quảng Bình", "Quảng Trị", "Thừa Thiên Huế", "Đà Nẵng", 
#         "Quảng Nam", "Quảng Ngãi", "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận"
#     ],
#     "south": [
#         "TP Hồ Chí Minh", "Cần Thơ", "An Giang", "Bạc Liêu", "Bến Tre", "Cà Mau", "Đồng Tháp", "Hậu Giang", 
#         "Kiên Giang", "Long An", "Sóc Trăng", "Tiền Giang", "Trà Vinh", "Vĩnh Long", "Bà Rịa–Vũng Tàu", 
#         "Bình Dương", "Bình Phước", "Đồng Nai", "Tây Ninh", "Kon Tum", "Gia Lai", "Đắk Lắk", "Đắk Nông", 
#         "Lâm Đồng"
#     ]
# }
# Danh sách các chủ đề
TOPICS = ["weather", "culture", "payment", "transport", "food", "service", "famous destination", "clothing", "shopping", "entertainment"]

# Prompt cải tiến
PROMPT_TEMPLATE = """
Bạn là một chatbot du lịch thông minh, bạn sẽ đóng vai làm 1 chuyên viên tư vấn du lịch cho 1 công ty du lịch Tour Guide.
Bạn sẽ tạo ra các câu hỏi và câu trả lời cho khách hàng về các chủ đề du lịch tại một thành phố/tỉnh cụ thể.
Các chủ đề sẽ xoay quanh các vấn đề liên quan đến du lịch cụ thể như dịch vụ được cung cấp bởi bên công ty Tour Guide.
Cụ thể hơn:
-Weather; Thời tiết thì thường khách sẽ hỏi về thời tiết tại địa điểm du lịch đó trong thời gian nào là đẹp nhất, thời điểm nào là mùa mưa, mùa khô, mùa đông, mùa hè và đi ở thời điểm nào để trải nghiệm 1 số thứ nhất định. (Không được sinh dữ liệu về theo kiểu chắc chắn thời tiết hôm nay, hay ngày mai vì bạn không thể cập nhật dataset liên tục về tình hình thời tiết bạn chỉ được áng chừng rằng đó là mùa đó có khả năng có thời tiêts gì).
-Culture; Văn hóa thì thường khách sẽ hỏi về các phong tục tập quán, lễ hội, thời gian tổ chức lễ hội/sự kiện ẩm thực đặc trưng của địa phương đó và khi đăng ký tour do bên công ty tổ chức thì khách hàng có được tham gia lễ hội hay trải nghiệm các phong tục tập quán của địa phương hay không/ trải nghiệm nhừng gì.
-Payment: Thì khách hàng sẽ hỏi về các hình thức thanh toán phổ biến của địa phương đó, có thể thanh toán bằng tiền mặt hay thẻ ngân hàng, có thể thanh toán bằng các ví điện tử hay không, địa điểm rút tiền.
-Transport: Khách hàng thường sẽ hỏi về các phương tiện sẽ được khách hàng sử dụng trong chuyến tour do bên công ty tổ chức, các phương tiện di chuyển từ địa điểm này đến địa điểm khác trong chuyến tour, các phương tiện di chuyển từ sân bay về khách sạn và ngược lại.
-Food: Khách hàng sẽ hỏi về các món ăn đặc trưng của địa phương đó, các món ăn nổi tiếng mà bên công ty tổ chức tour sẽ đưa khách hàng đi ăn, các món ăn mà bên công ty tổ chức tour sẽ phục vụ trong chuyến đi.
-Service: Khách hàng sẽ hỏi về các dịch vụ mà bên công ty tổ chức tour sẽ phục vụ trong chuyến đi, các dịch vụ mà bên công ty tổ chức tour sẽ cung cấp cho khách hàng trong chuyến đi, các dịch vụ mà bên công ty tổ chức tour sẽ không phục vụ trong chuyến đi.
-Famous destination: Khách hàng sẽ hỏi về các địa điểm nổi tiếng mà bên công ty tổ chức tour sẽ đưa khách hàng đi tham quan, các địa điểm nổi tiếng mà bên công ty tổ chức tour sẽ không đưa khách hàng đi tham quan, các địa điểm nổi tiếng mà bên công ty tổ chức tour sẽ không đưa khách hàng đi tham quan.
-Clothing: Khách hàng sẽ hỏi nên mặc gì khi đi du lịch tại địa phương đó ở thời điểm nào.
-Shopping: Khách hàng sẽ hỏi về các địa điểm mua sắm nổi tiếng tại địa phương đó, các địa điểm mua sắm nổi tiếng mà bên công ty tổ chức tour sẽ đưa khách hàng đi tham quan, các địa điểm mua sắm nổi tiếng mà bên công ty tổ chức tour sẽ không đưa khách hàng đi tham quan.
-Entertainment: Khách hàng sẽ hỏi về các địa điểm vui chơi giải trí nổi tiếng tại địa phương đó, các địa điểm vui chơi giải trí nổi tiếng mà bên công ty tổ chức tour sẽ đưa khách hàng đi tham quan, các địa điểm vui chơi giải trí nổi tiếng mà bên công ty tổ chức tour sẽ không đưa khách hàng đi tham quan.
Bạn sẽ tạo từ 1 đến 10 cặp câu hỏi và câu trả lời (Q&A) bằng tiếng Việt cho chatbot du lịch về chủ đề "{topic}" tại "{city}".(Lưu ý: Số lượng câu hỏi sẽ tương ứng với số lượng vấn đề mà khách hàng thường hỏi về chủ đề đó tại địa phương đó).
Mỗi Q&A phải có cấu trúc JSON sau:
{{
  "id": <số nguyên duy nhất>,
  "location": "{city}",
  "category": "{topic}",
  "question": "<câu hỏi cụ thể về {topic} tại {city}>",
  "answer": "<câu trả lời chi tiết, dưới 500 ký tự, chứa thông tin thực tế>",
  "sub_details": {{
    "season": "<mùa phù hợp hoặc null>",
    "suitable_for": "<đối tượng phù hợp hoặc null>",
    "additional_info": "<mẹo hoặc thông tin bổ sung>"
  }},
  "priority": 1,
  "tags": ["{topic}", "{city}", "<tag liên quan>"]
}}

Yêu cầu:
- "id" phải là số nguyên (integer), không phải chuỗi (string) id phải là duy nhất không được trùng lặp bắt đầu từ số 0.
- Tất cả nội dung phải bằng tiếng Việt.
- "sub_details" phải có đầy đủ "season", "suitable_for", và "additional_info".
- Không trùng lặp nội dung giữa các Q&A.
- Đảm bảo định dạng JSON hợp lệ.
"""

# class GeminiClient:
#     def __init__(self):
#         self.model = genai.GenerativeModel(
#             model_name="gemini-2.0-flash",
#             generation_config={"response_mime_type": "application/json"}
#         )

#     async def generate_faq(self, prompt, retries=3):
#         for attempt in range(1, retries + 1):
#             try:
#                 response = await self.model.generate_content_async(
#                     contents=prompt,
#                     generation_config={"temperature": 0.5, "max_output_tokens": 2000}
#                 )
#                 text = response.text.strip()
#                 try:
#                     data = json.loads(text)
#                     if isinstance(data, list):
#                         return data
#                     else:
#                         raise ValueError("Expected a list of JSON objects")
#                 except json.JSONDecodeError as e:
#                     logging.error(f"JSON parsing error: {str(e)}")
#                     logging.debug(f"Raw response: {text}")
#                     m = re.search(r"\[.*\]", text, re.DOTALL)
#                     if m:
#                         try:
#                             return json.loads(m.group(0))
#                         except json.JSONDecodeError:
#                             pass
#                     raise ValueError(f"Invalid JSON format: {str(e)}")
#             except Exception as e:
#                 error_msg = str(e).lower()
#                 if any(x in error_msg for x in ["rate limit", "quota", "server error"]):
#                     if attempt < retries:
#                         logging.warning(f"Attempt {attempt} failed: {error_msg}. Retrying after {attempt}s...")
#                         await asyncio.sleep(attempt)
#                         continue
#                 logging.error(f"Error generating FAQ: {error_msg}")
#                 return []
#         logging.error("Max retries reached. Returning empty list.")
#         return []

class GeminiClient:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"response_mime_type": "application/json"}
        )

    async def generate_faq(self, prompt, retries=3):
        for attempt in range(1, retries + 1):
            try:
                response = await self.model.generate_content_async(
                    contents=prompt,
                    generation_config={"temperature": 0.5, "max_output_tokens": 2000}
                )
                text = response.text.strip()
                logging.debug(f"Raw response: {text[:500]}...")
                
                # Thử parse JSON trực tiếp
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        return data
                    else:
                        raise ValueError("Expected a list of JSON objects")
                except json.JSONDecodeError as e:
                    logging.error(f"JSON parsing error: {str(e)}")
                    # Thử sửa JSON bằng regex
                    match = re.search(r"\[.*\]", text, re.DOTALL)
                    if match:
                        try:
                            fixed_json = match.group(0).replace("\n", "").strip()
                            data = json.loads(fixed_json)
                            if isinstance(data, list):
                                logging.info("Successfully fixed JSON using regex")
                                return data
                        except json.JSONDecodeError as e2:
                            logging.error(f"Failed to fix JSON with regex: {str(e2)}")
                    # Thử trích xuất từng object
                    objects = re.findall(r"\{[^}]*\}", text, re.DOTALL)
                    if objects:
                        fixed_data = []
                        for obj in objects:
                            try:
                                fixed_obj = obj.replace("\n", "").strip()
                                fixed_data.append(json.loads(fixed_obj))
                                logging.info("Successfully extracted individual JSON object")
                            except json.JSONDecodeError as e3:
                                logging.error(f"Failed to parse object: {str(e3)}")
                        if fixed_data:
                            return fixed_data
                    raise ValueError(f"Invalid JSON format after attempts: {str(e)}")

            except Exception as e:
                error_msg = str(e).lower()
                if any(x in error_msg for x in ["rate limit", "quota", "server error"]):
                    if attempt < retries:
                        logging.warning(f"Attempt {attempt} failed: {error_msg}. Retrying after {attempt}s...")
                        await asyncio.sleep(attempt)
                        continue
                logging.error(f"Error generating FAQ: {error_msg}")
                return []
        logging.error("Max retries reached. Returning empty list.")
        return []
    
# def validate_qa_pairs(qa_pairs, start_id):
#     valid_pairs = []
#     current_id = start_id
#     seen = set()  # Kiểm tra trùng lặp
#     for qa in qa_pairs:
#         qa_copy = qa.copy()
#         # Chuyển "id" thành số nguyên
#         if "id" in qa_copy:
#             try:
#                 qa_copy["id"] = int(qa_copy["id"])
#             except (ValueError, TypeError):
#                 qa_copy["id"] = current_id
#                 current_id += 1
#         else:
#             qa_copy["id"] = current_id
#             current_id += 1
#         # Kiểm tra trùng lặp
#         question = qa_copy.get("question", "")
#         answer = qa_copy.get("answer", "")
#         if (question, answer) in seen:
#             logging.warning(f"Duplicate QA pair skipped: {question}")
#             continue
#         seen.add((question, answer))
#         # Đảm bảo sub_details đầy đủ
#         if "sub_details" not in qa_copy or not isinstance(qa_copy["sub_details"], dict):
#             qa_copy["sub_details"] = {"season": None, "suitable_for": None, "additional_info": "Không có thông tin bổ sung."}
#         else:
#             sub_details = qa_copy["sub_details"]
#             sub_details.setdefault("season", None)
#             sub_details.setdefault("suitable_for", None)
#             sub_details.setdefault("additional_info", "Không có thông tin bổ sung.")
#         try:
#             validate(qa_copy, SCHEMA)
#             valid_pairs.append(qa_copy)
#         except ValidationError as ve:
#             logging.warning(f"Invalid QA pair skipped: {qa_copy}. Error: {ve.message}")
#     return valid_pairs, current_id

# async def main(group_name):
#     if group_name not in GROUPS:
#         print(f"Group {group_name} not found. Available groups: {list(GROUPS.keys())}")
#         return

#     client = GeminiClient()
#     all_faq = []
#     start_id = 0
#     locations = GROUPS[group_name]

#     for city in locations:
#         for topic in TOPICS:
#             print(f"Generating FAQ for {city} - {topic}")
#             prompt = PROMPT_TEMPLATE.format(city=city, topic=topic)
#             qa_pairs = await client.generate_faq(prompt)
#             valid_pairs, start_id = validate_qa_pairs(qa_pairs, start_id)
#             all_faq.extend(valid_pairs)
#             print(f"Generated {len(valid_pairs)} valid Q&A for {city} - {topic}")

#     output_file = f"/Users/nguyen_bao/Documents/PTIT/Junior_2/ltw/Chatbot_AI/data/raw/faq_{group_name}.json"
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)
#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(all_faq, f, ensure_ascii=False, indent=2)
#     print(f"Đã tạo {len(all_faq)} mục Q&A vào {output_file}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Generate FAQ data for specific regions in Vietnam.")
#     parser.add_argument("--group", choices=["north", "central", "south"], required=True, help="Region to generate FAQs for (north, central, south)")
#     args = parser.parse_args()
#     asyncio.run(main(args.group))

def validate_qa_pairs(qa_pairs, start_id):
    valid_pairs = []
    current_id = start_id
    seen = set()  # Kiểm tra trùng lặp
    for qa in qa_pairs:
        qa_copy = qa.copy()

        # Gán id duy nhất không phụ thuộc input
        qa_copy["id"] = current_id
        current_id += 1

        # Kiểm tra trùng lặp
        question = qa_copy.get("question", "")
        answer = qa_copy.get("answer", "")
        if (question, answer) in seen:
            logging.warning(f"Duplicate QA pair skipped: {question}")
            continue
        seen.add((question, answer))

        # Đảm bảo sub_details đầy đủ
        if "sub_details" not in qa_copy or not isinstance(qa_copy["sub_details"], dict):
            qa_copy["sub_details"] = {"season": None, "suitable_for": None, "additional_info": "Không có thông tin bổ sung."}
        else:
            sub_details = qa_copy["sub_details"]
            sub_details.setdefault("season", None)
            sub_details.setdefault("suitable_for", None)
            sub_details.setdefault("additional_info", "Không có thông tin bổ sung.")

        # Validate schema
        try:
            validate(qa_copy, SCHEMA)
            valid_pairs.append(qa_copy)
        except ValidationError as ve:
            logging.warning(f"Invalid QA pair skipped: {qa_copy}. Error: {ve.message}")
    return valid_pairs, current_id

async def main(group_name):
    if group_name not in GROUPS:
        print(f"Group {group_name} not found. Available groups: {list(GROUPS.keys())}")
        return

    client = GeminiClient()
    all_faq = []
    start_id = 0
    locations = GROUPS[group_name]

    for city in locations:
        for topic in TOPICS:
            print(f"Generating FAQ for {city} - {topic}")
            prompt = PROMPT_TEMPLATE.format(city=city, topic=topic)
            qa_pairs = await client.generate_faq(prompt)
            valid_pairs, start_id = validate_qa_pairs(qa_pairs, start_id)
            # start_id += 5  # Cập nhật ID bắt đầu cho lần tiếp theo
            all_faq.extend(valid_pairs)
            print(f"Generated {len(valid_pairs)} valid Q&A for {city} - {topic}")

    output_file = f"/Users/nguyen_bao/Documents/PTIT/Junior_2/ltw/Chatbot_AI/data/raw/faqupdate_{group_name}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_faq, f, ensure_ascii=False, indent=2)
    print(f"Đã tạo {len(all_faq)} mục Q&A vào {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate FAQ data for specific regions in Vietnam.")
    parser.add_argument("--group", choices=["north", "central", "south"], required=True, help="Region to generate FAQs for (north, central, south)")
    args = parser.parse_args()
    asyncio.run(main(args.group))