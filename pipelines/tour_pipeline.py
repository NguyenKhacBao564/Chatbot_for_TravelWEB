
import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification, pipeline
from vncorenlp import VnCoreNLP
from dateutil.parser import parse
from datetime import datetime, timedelta
import logging
import re
import os
import calendar
import torch
from extractors.extract_location import extract_location
from extractors.extract_time import extract_all_times
from extractors.extract_price import extract_price_vn
from pydantic import BaseModel
from google_genAI import get_genai_response
from pipelines.retrieval import RetrievalPipeline


# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))


class ResetRequest(BaseModel):
    user_id: str = "default_user"

class SessionManager:
    """Quản lý session người dùng với TTL."""
    def __init__(self, ttl_hours=24):
        self.sessions = {}
        self.ttl = timedelta(hours=ttl_hours)

    def get_session(self, user_id):
        if user_id not in self.sessions or self._is_expired(user_id):
            self.sessions[user_id] = {
                "location": None, "time": None, "price": None,
                "last_updated": datetime.now(), "search_history": []
            }
        return self.sessions[user_id]

    def _is_expired(self, user_id):
        session = self.sessions.get(user_id, {})
        last_updated = session.get("last_updated")
        return last_updated and (datetime.now() - last_updated) > self.ttl

    def reset_session(self, user_id):
        self.sessions[user_id] = {
            "location": None, "time": None, "price": None,
            "last_updated": datetime.now(), "search_history": []
        }
        logger.debug(f"Reset session for user_id: {user_id}")

class TourRetrievalPipeline:
    """Pipeline để tìm kiếm và trả lời thông tin tour du lịch."""
    INTENT_LABELS = {
        0: "find_tour_with_location",
        1: "find_tour_with_time",
        2: "find_tour_with_price",
        3: "find_tour_with_location_and_time",
        4: "find_tour_with_location_and_price",
        5: "find_tour_with_time_and_price",
        6: "find_with_all",
        7: "out_of_scope"
     }

    def __init__(self):

        # Load SentenceTransformer
        self.retrievalPipeline = RetrievalPipeline()

        # Load PhoBERT cho phân loại ý định
        model_intent_path = "training/phobert_intent_finetuned"
        self.intent_tokenizer = AutoTokenizer.from_pretrained(model_intent_path)
        self.intent_model = AutoModelForSequenceClassification.from_pretrained(model_intent_path)
        # self.intent_labels = {0: "find_tour_with_location", 1: "find_tour_with_location_and_time", 2: "find_tour_with_location_and_price", 3: "out_of_scope"}


        jar_path = "training/VnCoreNLP-1.1.1.jar"
        try:
            self.vncorenlp = VnCoreNLP(jar_path, annotators="wseg,pos,ner", max_heap_size='-Xmx2g')
        except Exception as e:
            logger.error(f"Không thể khởi tạo VnCoreNLP: {e}")
            raise

        self.session_manager = SessionManager()
        logger.info("Khởi tạo TourRetrievalPipeline thành công!")

    def extract_intent(self, query):
        try:
            inputs = self.intent_tokenizer(query, return_tensors="pt", max_length=128, truncation=True, padding=True)
            with torch.no_grad():
                outputs = self.intent_model(**inputs)
            predicted_class = torch.argmax(outputs.logits, dim=1).item()
            return self.INTENT_LABELS[predicted_class]
        except Exception as e:
            logger.error(f"Lỗi phân loại ý định: {e}")
            return "out_of_scope"

    def extract_entities(self, query,intent, user_id="default_user"):
        session = self.session_manager.get_session(user_id)
        location = session["location"]
        time = session["time"]
        price = session["price"]


        if intent in ["find_tour_with_location", "find_tour_with_location_and_time", "find_tour_with_location_and_price", "find_with_all"]:
            extracted_location = extract_location(query)
            if extracted_location != "None":
                location = extracted_location
                session["location"] = location
                logger.debug(f"Extracted location: {location}")

        if intent in  ["find_tour_with_location_and_time", "find_tour_with_time", "find_tour_with_time_and_price", "find_with_all"]:
            extracted_time = extract_all_times(query)
            if extracted_time != "None":
                time = extracted_time
                session["time"] = time
                logger.debug(f"Extracted time: {time}")

        if intent in ["find_tour_with_location_and_price", "find_tour_with_price", "find_tour_with_time_and_price", "find_with_all"]:
            extracted_price = extract_price_vn(query)
            if extracted_price != "None":
                price = extracted_price
                session["price"] = price    
                logger.debug(f"Extracted price: {price}")
       
        session["last_updated"] = datetime.now()
        session["search_history"].append({"query": query})
        logger.debug(f"Extracted entities: location={location}, time={time}, price={price}")
        return {"location": location, "time": time, "price": price}

    def reset_session(self, user_id):
            self.session_manager.reset_session(user_id)
            logger.debug(f"Session reset for user_id: {user_id}")

    def get_faq_response(self, query, k=1):
        try:
            respond = self.retrievalPipeline.get_retrieved_context(query, top_k=k)
            if respond == "None":
                respond = get_genai_response(
                "Trả lời là 'Tôi chỉ trả lời các câu hỏi liên quan đến vấn đề du lịch hoặc tư vấn 1 tour du lịch phù hợp cho bạn' một cách lịch sự và ngắn gọn"
            )
            else:
                respond = get_genai_response(
                    "Với câu hỏi này: '" + query + "' và tôi đưa ra câu trả lời này: '" + respond + "'. Nếu câu trả lời không liên quan đến câu hỏi thì hãy trả lời một cách tự nhiên câu sau 'Tôi chỉ trả lời các câu hỏi liên quan đến vấn đề du lịch hoặc tư vấn 1 tour du lịch phù hợp cho bạn. Mong bạn thông cảm' còn nếu phù hợp thì không cần bảo gì ngoài đưa ra chính xác câu trả lời đó(không cần giải thích gì cả)!" 
                )
            # chat_response_text = get_genai_response(
            #     "Kiểm tra xem câu query này: '" + query + "' và câu trả lời này: '" + respond + 
            #     "' có phù hợp không, nếu phù hợp thì trả về đúng câu trả lời đó, nếu không thì chỉ cần trả lời là 'Tôi chỉ trả lời các câu hỏi liên quan đến vấn đề du lịch hoặc tư vấn 1 tour du lịch phù hợp cho bạn' "
            # )
            return {
                "response": respond,
            }
        except Exception as e:
            logger.error(f"Lỗi tìm FAQ với KNN: {e}")
            return {
                "response": "Dạ, em chưa hiểu ý bạn. Bạn có thể hỏi về tour hoặc đặt phòng khách sạn không ạ?",
            }

    def get_tour_response(self, query, user_id="default_user"):
        intent = self.extract_intent(query)
        print("intent: ", intent)
        if intent == "out_of_scope":
            faq_response = self.get_faq_response(query)
            return {
                    "status": "faq",
                    "response": f"{faq_response['response']}",
                    "location": "None",
                    "time": "None",
                    "price": "None"
                }
        
        info = self.extract_entities(query, intent, user_id)

        missing_info = []
        if not info["location"]:
            missing_info.append("Điểm đến (ví dụ: Đà Lạt, Hà Nội, Phú Quốc,...)")
        if not info["time"]:
            missing_info.append("Thời gian khởi hành (ví dụ: tháng 12, 25/5,...)")
        if not info["price"]:
            missing_info.append("Giá (ví dụ: 5 triệu, 20m,...)")

        if missing_info:
            prompt = (
                f"Người dùng đã cung cấp thông tin về tour du lịch: "
                f"Địa điểm: {info['location'] or 'chưa có'}, "
                f"Thời gian: {info['time'] or 'chưa có'}, "
                f"Giá: {info['price'] or 'chưa có'}. "
                f"Vui lòng viết một câu trả lời lịch sự bằng tiếng Việt, xác nhận thông tin đã nhận và yêu cầu cung cấp các thông tin còn thiếu (thông tin sẽ cung cấp sau không cần nói ra cụ thể) "
                f"Nói kiểu câu cuối cùng có dấu :"
                f"Ví dụ: 'Dạ, em đã ghi nhận thông tin quý khách muốn tìm tour đến [địa điểm]/[thời gian khởi hành]/[giá tour]. Xin quý khách vui lòng cho em biết thêm thông tin như:'"
            )
            try:
                response_text = get_genai_response(prompt)
                return {
                    "status": "missing_info",
                    "response": f"{response_text}\n- " + "\n- ".join(missing_info),
                    "location": info['location'] or "None",
                    "time": info['time'] or "None",
                    "price": info['price'] or "None"
                }
            except Exception as e:
                logger.error(f"Lỗi gọi Gemini API: {e}")
                return {
                    "status": "missing_info",
                    "response": "Dạ, để tìm tour phù hợp, em cần bạn cung cấp thêm:\n- " + "\n- ".join(missing_info),
                    "location": info['location'] or "None",
                    "time": info['time'] or "None",
                    "price": info['price'] or "None"
                }
        # Đủ thông tin thì tìm kiếm
        prompt = (
                f"Đã có các thông tin về tour du lịch: "
                f"Địa điểm: {info['location']}, "
                f"Thời gian: {info['time']}, "
                f"Giá: {info['price']}. "
                f"Vui lòng viết một câu trả lời lịch sự bằng tiếng Việt, xác nhận thông tin đã nhận và đưa ra câu mở đầu trước khi liệt kê các tour đã tìm được. "
                f"Nói kiểu câu cuối cùng có dấu :"
                f"Ví dụ: 'Dạ, em đã tìm được một số tour phù hợp như: "
            )
        response_text = get_genai_response(prompt)
        response_obj = {
            "status": "success",
            "response": f"{response_text}",
            "location": info['location'] or "None",
            "time": info['time'] or "None",
            "price": info['price'] or "None"
        }
        self.reset_session("default_user")
        return response_obj




# if __name__ == "__main__":
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     pipeline = TourRetrievalPipeline(
#         index_file=os.path.join(current_dir, "faq_index.faiss"),
#         metadata_file=os.path.join(current_dir, "faq_metadata.json")
#     )
#     user_id = "test_user"
#     while True:
#         user_query = input("Bạn: ")
#         if user_query.lower() in ["exit", "quit"]:
#             break
#         response = pipeline.get_tour_response(user_query, user_id=user_id)
#         print(f"Bot: {response}")


