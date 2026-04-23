import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError:
    torch = None
    AutoModelForSequenceClassification = None
    AutoTokenizer = None

from extractors.extract_location import extract_location
from extractors.extract_price import extract_price_vn
from extractors.extract_time import extract_all_times
from google_genAI import get_genai_response
from pipelines.retrieval import RetrievalPipeline
from schemas.chat_response import ChatResponse
from schemas.tour_models import ExtractedEntities
from services.entity_normalizer import (
    extract_destination_from_text,
    normalize_entities,
    to_search_filters,
)
from services.tour_search_service import TourSearchService


logger = logging.getLogger(__name__)


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@dataclass
class SearchDecision:
    can_search: bool
    is_partial: bool
    missing_fields: list[str]


class SessionManager:
    """In-memory per-user session manager with TTL."""

    def __init__(self, ttl_hours=24):
        self.sessions = {}
        self.ttl = timedelta(hours=ttl_hours)

    def get_session(self, user_id):
        if user_id not in self.sessions or self._is_expired(user_id):
            self.sessions[user_id] = self._new_session()
        return self.sessions[user_id]

    def _is_expired(self, user_id):
        session = self.sessions.get(user_id, {})
        last_updated = session.get("last_updated")
        return last_updated and (datetime.now() - last_updated) > self.ttl

    def reset_session(self, user_id):
        self.sessions[user_id] = self._new_session()
        logger.debug("Reset session for user_id=%s", user_id)

    @staticmethod
    def _new_session():
        return {
            "location": None,
            "time": None,
            "price": None,
            "last_updated": datetime.now(),
            "search_history": [],
        }


class TourRetrievalPipeline:
    """NLP orchestration layer for travel chatbot requests."""

    INTENT_LABELS = {
        0: "find_tour_with_location",
        1: "find_tour_with_time",
        2: "find_tour_with_price",
        3: "find_tour_with_location_and_time",
        4: "find_tour_with_location_and_price",
        5: "find_tour_with_time_and_price",
        6: "find_with_all",
        7: "out_of_scope",
    }

    LOCATION_INTENTS = {
        "find_tour_with_location",
        "find_tour_with_location_and_time",
        "find_tour_with_location_and_price",
        "find_with_all",
    }
    TIME_INTENTS = {
        "find_tour_with_location_and_time",
        "find_tour_with_time",
        "find_tour_with_time_and_price",
        "find_with_all",
    }
    PRICE_INTENTS = {
        "find_tour_with_location_and_price",
        "find_tour_with_price",
        "find_tour_with_time_and_price",
        "find_with_all",
    }

    def __init__(
        self,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        tour_search_service: Optional[TourSearchService] = None,
        load_models: bool = True,
        intent_model_path: str = "training/phobert_intent_finetuned",
    ):
        self.retrievalPipeline = retrieval_pipeline
        if self.retrievalPipeline is None:
            try:
                self.retrievalPipeline = RetrievalPipeline()
            except Exception as exc:
                logger.warning("FAQ retrieval pipeline is unavailable: %s", exc)

        self.tour_search_service = tour_search_service or TourSearchService()
        self.intent_tokenizer = None
        self.intent_model = None

        if load_models:
            self._load_intent_model(intent_model_path)

        self.session_manager = SessionManager()
        logger.info("TourRetrievalPipeline initialized")

    def _load_intent_model(self, model_path: str):
        if torch is None or AutoTokenizer is None or AutoModelForSequenceClassification is None:
            logger.warning("Torch/Transformers are not installed, using rule-based intent fallback")
            return
        try:
            self.intent_tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.intent_model = AutoModelForSequenceClassification.from_pretrained(model_path)
        except Exception as exc:
            logger.warning("Intent model unavailable, using rule-based fallback: %s", exc)

    def extract_intent(self, query):
        if self.intent_tokenizer is None or self.intent_model is None:
            return self._extract_intent_fallback(query)

        try:
            inputs = self.intent_tokenizer(
                query,
                return_tensors="pt",
                max_length=128,
                truncation=True,
                padding=True,
            )
            with torch.no_grad():
                outputs = self.intent_model(**inputs)
            predicted_class = torch.argmax(outputs.logits, dim=1).item()
            return self.INTENT_LABELS.get(predicted_class, "out_of_scope")
        except Exception as exc:
            logger.error("Intent classification failed: %s", exc)
            return self._extract_intent_fallback(query)

    def _extract_intent_fallback(self, query):
        query_lower = query.lower()
        has_location = bool(extract_destination_from_text(query)[1])
        has_time = extract_all_times(query) is not None
        has_price = extract_price_vn(query) is not None
        looks_like_tour_query = any(
            keyword in query_lower
            for keyword in ["tour", "du lịch", "đi ", "khởi hành", "giá", "ngân sách"]
        )
        if not looks_like_tour_query and not (has_location or has_time or has_price):
            return "out_of_scope"

        if has_location and has_time and has_price:
            return "find_with_all"
        if has_location and has_time:
            return "find_tour_with_location_and_time"
        if has_location and has_price:
            return "find_tour_with_location_and_price"
        if has_time and has_price:
            return "find_tour_with_time_and_price"
        if has_location:
            return "find_tour_with_location"
        if has_time:
            return "find_tour_with_time"
        if has_price:
            return "find_tour_with_price"
        return "out_of_scope"

    def extract_entities(self, query, intent, user_id="default_user"):
        session = self.session_manager.get_session(user_id)
        location = session["location"]
        time = session["time"]
        price = session["price"]

        if intent in self.LOCATION_INTENTS:
            extracted_location = extract_location(query)
            if extracted_location is not None:
                location = extracted_location
                session["location"] = location
                logger.debug("Extracted location=%s", location)
            else:
                fallback_location, _ = extract_destination_from_text(query)
                if fallback_location:
                    location = fallback_location
                    session["location"] = location
                    logger.debug("Extracted location by alias=%s", location)

        if intent in self.TIME_INTENTS:
            extracted_time = extract_all_times(query)
            if extracted_time is not None:
                time = extracted_time
                session["time"] = time
                logger.debug("Extracted time=%s", time)

        if intent in self.PRICE_INTENTS:
            extracted_price = extract_price_vn(query)
            if extracted_price is not None:
                price = extracted_price
                session["price"] = price
                logger.debug("Extracted price=%s", price)

        raw_entities = {"location": location, "time": time, "price": price}
        normalized = normalize_entities(raw_entities, query)
        if normalized.location:
            session["location"] = normalized.location

        session["last_updated"] = datetime.now()
        session["search_history"].append({"query": query, "intent": intent})
        return normalized

    def reset_session(self, user_id):
        self.session_manager.reset_session(user_id)

    def get_faq_response(self, query, k=3):
        fallback_message = (
            "Dạ, em chỉ hỗ trợ các câu hỏi liên quan đến du lịch hoặc tư vấn tour phù hợp. "
            "Mong bạn thông cảm."
        )
        if self.retrievalPipeline is None:
            return fallback_message, []

        try:
            sources = self.retrievalPipeline.retrieve(query, top_k=k)
            if not sources:
                return fallback_message, []

            answer = sources[0].answer or fallback_message
            prompt = (
                "Hãy diễn đạt lại câu trả lời sau bằng tiếng Việt tự nhiên, ngắn gọn, "
                "không thêm thông tin mới ngoài nội dung được cung cấp.\n"
                f"Câu trả lời gốc: {answer}"
            )
            message = get_genai_response(prompt, fallback=answer)
            return message or answer, sources
        except Exception as exc:
            logger.error("FAQ retrieval failed: %s", exc)
            return fallback_message, []

    def get_tour_response(self, query, user_id="default_user"):
        intent = self.extract_intent(query)
        logger.info("Detected intent=%s user_id=%s", intent, user_id)

        if intent == "out_of_scope":
            message, faq_sources = self.get_faq_response(query)
            response = ChatResponse(
                status="faq",
                message=message,
                entities=ExtractedEntities(),
                missing_fields=[],
                tours=[],
                faq_sources=faq_sources,
            )
            return self._to_response_dict(response)

        entities = self.extract_entities(query, intent, user_id)
        search_decision = self._assess_search_state(entities)
        missing_fields = search_decision.missing_fields

        if not search_decision.can_search:
            response = ChatResponse(
                status="missing_info",
                message=self._missing_info_message(entities, missing_fields),
                entities=entities,
                missing_fields=missing_fields,
                tours=[],
                faq_sources=[],
            )
            return self._to_response_dict(response)

        search_filters = to_search_filters(entities)
        tours = self.tour_search_service.search(search_filters)
        if search_decision.is_partial:
            status = "partial_search"
        else:
            status = "success" if tours else "no_results"
        message = self._tour_search_message(
            entities=entities,
            total_results=len(tours),
            is_partial=search_decision.is_partial,
            missing_fields=missing_fields,
        )

        if status == "success":
            self.reset_session(user_id)

        response = ChatResponse(
            status=status,
            message=message,
            entities=entities,
            missing_fields=missing_fields,
            tours=tours,
            faq_sources=[],
        )
        return self._to_response_dict(response)

    @staticmethod
    def _has_location(entities: ExtractedEntities) -> bool:
        return bool(entities.destination_normalized)

    @staticmethod
    def _has_time(entities: ExtractedEntities) -> bool:
        return bool(entities.date_start and entities.date_end)

    @staticmethod
    def _has_price(entities: ExtractedEntities) -> bool:
        return entities.price_min is not None or entities.price_max is not None

    def _assess_search_state(self, entities: ExtractedEntities) -> SearchDecision:
        has_location = self._has_location(entities)
        has_time = self._has_time(entities)
        has_price = self._has_price(entities)

        if not has_location:
            return SearchDecision(can_search=False, is_partial=False, missing_fields=["location"])

        if not (has_time or has_price):
            return SearchDecision(
                can_search=False,
                is_partial=False,
                missing_fields=["time", "price"],
            )

        missing_fields = []
        if not has_time:
            missing_fields.append("time")
        if not has_price:
            missing_fields.append("price")

        return SearchDecision(
            can_search=True,
            is_partial=bool(missing_fields),
            missing_fields=missing_fields,
        )

    def _missing_info_message(self, entities: ExtractedEntities, missing_fields):
        if "location" in missing_fields:
            if self._has_time(entities) or self._has_price(entities):
                known_filters = []
                if self._has_time(entities):
                    known_filters.append("thời gian")
                if self._has_price(entities):
                    known_filters.append("ngân sách")
                known_text = " và ".join(known_filters)
                fallback = (
                    f"Dạ, em đã ghi nhận {known_text} của quý khách. "
                    "Quý khách cho em xin thêm điểm đến để em tìm tour phù hợp."
                )
            else:
                fallback = (
                    "Dạ, để em bắt đầu tìm tour phù hợp, quý khách cho em xin điểm đến mong muốn nhé."
                )
            prompt = (
                "Viết một câu tiếng Việt lịch sự để xin thêm điểm đến cho việc tìm tour. "
                f"Thông tin đã có: {model_to_dict(entities)}."
            )
            return get_genai_response(prompt, fallback=fallback) or fallback

        fallback = (
            f"Dạ, em đã ghi nhận điểm đến {entities.location}. "
            "Quý khách cho em xin thêm thời gian khởi hành hoặc ngân sách dự kiến để em bắt đầu tìm tour phù hợp."
        )
        prompt = (
            "Viết một câu tiếng Việt lịch sự để xin thêm ít nhất một điều kiện tìm tour. "
            "Yêu cầu khách bổ sung thời gian khởi hành hoặc ngân sách dự kiến. "
            f"Thông tin đã có: {model_to_dict(entities)}."
        )
        return get_genai_response(prompt, fallback=fallback) or fallback

    def _tour_search_message(
        self,
        entities: ExtractedEntities,
        total_results: int,
        is_partial: bool,
        missing_fields: list[str],
    ):
        if is_partial:
            missing_label = "thời gian khởi hành" if "time" in missing_fields else "ngân sách dự kiến"
            known_label = "ngân sách hiện có" if "time" in missing_fields else "thời gian hiện có"
            if total_results == 0:
                fallback = (
                    f"Dạ, hiện em chưa tìm thấy tour phù hợp với điểm đến và {known_label}. "
                    f"Quý khách có thể cho em thêm {missing_label} hoặc điều chỉnh tiêu chí để em lọc lại."
                )
            else:
                fallback = (
                    f"Dạ, em tìm được {total_results} tour phù hợp với điểm đến và {known_label}. "
                    f"Quý khách có thể cho em thêm {missing_label} để em lọc sát hơn."
                )
            prompt = (
                "Viết một câu tiếng Việt ngắn, lịch sự cho kết quả tìm tour theo điều kiện chưa đầy đủ. "
                "Nếu có tour, nói đã tìm được tour và gợi ý khách bổ sung điều kiện còn thiếu để lọc sát hơn. "
                "Nếu không có tour, nói chưa tìm thấy tour và gợi ý khách bổ sung điều kiện còn thiếu hoặc đổi tiêu chí. "
                f"Số tour tìm được: {total_results}. Điều kiện còn thiếu: {missing_fields}. "
                f"Bộ lọc hiện có: {model_to_dict(entities)}."
            )
            return get_genai_response(prompt, fallback=fallback) or fallback

        if total_results == 0:
            return (
                "Dạ, hiện em chưa tìm thấy tour phù hợp với điểm đến, thời gian và ngân sách này. "
                "Quý khách có thể thử đổi ngày khởi hành hoặc ngân sách."
            )

        fallback = f"Dạ, em tìm được {total_results} tour phù hợp:"
        prompt = (
            "Viết một câu mở đầu ngắn bằng tiếng Việt trước khi hiển thị danh sách tour. "
            "Không thêm thông tin tour cụ thể. "
            f"Số tour tìm được: {total_results}. Bộ lọc: {model_to_dict(entities)}."
        )
        return get_genai_response(prompt, fallback=fallback) or fallback

    @staticmethod
    def _to_response_dict(response: ChatResponse):
        if hasattr(response, "model_dump_json"):
            return json.loads(response.model_dump_json())
        return json.loads(response.json())
