import json
import logging
import re
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
from schemas.chat_response import ChatResponse, FAQSource
from schemas.tour_models import ExtractedEntities
from services.entity_normalizer import (
    extract_destination_from_text,
    normalize_entities,
    slugify_vietnamese,
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

    def __init__(self, ttl_hours=24, context_ttl_minutes=30):
        self.sessions = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.context_ttl = timedelta(minutes=context_ttl_minutes)

    def get_session(self, user_id):
        if user_id not in self.sessions or self._is_expired(user_id):
            self.sessions[user_id] = self._new_session()
        if "conversation_context" not in self.sessions[user_id]:
            self.sessions[user_id]["conversation_context"] = self._new_conversation_context()
        return self.sessions[user_id]

    def _is_expired(self, user_id):
        session = self.sessions.get(user_id, {})
        last_updated = session.get("last_updated")
        return last_updated and (datetime.now() - last_updated) > self.ttl

    def reset_session(self, user_id):
        self.sessions[user_id] = self._new_session()
        logger.debug("Reset session for user_id=%s", user_id)

    def reset_search_state(self, user_id):
        """Clear search slots while preserving lightweight conversation context."""
        session = self.get_session(user_id)
        session["location"] = None
        session["time"] = None
        session["price"] = None
        session["search_history"] = []
        session["last_updated"] = datetime.now()
        logger.debug("Reset search state for user_id=%s", user_id)

    def get_conversation_context(self, user_id):
        session = self.get_session(user_id)
        context = session.get("conversation_context")
        if not context or self._is_context_expired(context):
            context = self._new_conversation_context()
            session["conversation_context"] = context
        return context

    def _is_context_expired(self, context):
        last_updated = context.get("last_updated")
        return last_updated and (datetime.now() - last_updated) > self.context_ttl

    @staticmethod
    def _new_session():
        return {
            "location": None,
            "time": None,
            "price": None,
            "last_updated": datetime.now(),
            "search_history": [],
            "conversation_context": SessionManager._new_conversation_context(),
        }

    @staticmethod
    def _new_conversation_context():
        return {
            "last_location": None,
            "last_location_normalized": None,
            "last_time": None,
            "last_topic": None,
            "last_topics": [],
            "last_mode": None,
            "last_query": None,
            "last_updated": None,
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
    KNOWLEDGE_QUERY_PATTERNS = {
        # food
        "an-gi",
        "mon-gi",
        "mon-an",
        "an-uong",
        "am-thuc",
        "dac-san",
        "ca-phe",
        "quan-ca-phe",
        "quan-an",
        "nha-hang",
        "phai-thu",
        # weather
        "thoi-tiet",
        "khi-hau",
        "nang-khong",
        "mua-khong",
        "nhiet-do",
        "nong-khong",
        "lanh-khong",
        "ret-khong",
        # culture
        "van-hoa",
        "le-hoi",
        "lich-su",
        "phong-tuc",
        "tap-quan",
        "ngon-ngu",
        "dan-toc",
        # clothing
        "mac-gi",
        "mac-do",
        "nen-mac",
        "trang-phuc",
        "quan-ao",
        "chuan-bi-gi",
        "mang-gi",
        "do-gi",
        "giay-dep",
        "ao-khoac",
        # activities / places
        "mua-gi",
        "choi-gi",
        "gi-choi",
        "di-dau",
        "nen-di",
        "nen-ghe",
        "tham-quan-gi",
        "gi-vui",
        "gi-hay",
        "gi-dep",
        "noi-tieng",
        "o-dau",
        "check-in",
        "dia-diem",
        # transport
        "phuong-tien",
        "di-chuyen",
        "di-lai",
        "cach-di",
        "den-bang-gi",
        "xe-khach",
        "may-bay",
        "tau-hoa",
        "tau-thuyen",
        "thue-xe",
        # distance / logistics
        "bao-nhieu-km",
        "cach-bao-xa",
        # safety
        "an-ninh",
        "an-toan",
        # shopping / entertainment
        "mua-sam",
        "cho-dem",
        "cho-nao",
        # tour service / policy (NOT tour search)
        "huy-tour",
        "doi-lich",
        "thay-doi-lich",
        "hoan-tien",
        "chinh-sach",
        "bao-hiem",
        "thanh-toan",
        "tra-gop",
        "dat-coc",
        "thu-tuc",
        "ho-tro",
        "khieu-nai",
        "dich-vu",
        "phien-dich",
        "huong-dan-vien",
        "hanh-ly",
        "khach-san",
        "dat-phong",
        "visa",
        "ho-chieu",
        "thu-cung",
        "wifi",
        "tre-em",
        "tre-nho",
        "do-tuoi",
        "mua-ve",
    }
    # Patterns that signal a service/policy FAQ even when "tour" is present
    SERVICE_QUERY_PATTERNS = {
        "huy-tour",
        "doi-lich",
        "thay-doi-lich",
        "thay-doi",
        "hoan-tien",
        "chinh-sach",
        "bao-hiem",
        "thanh-toan",
        "tra-gop",
        "dat-coc",
        "thu-tuc",
        "ho-tro",
        "khieu-nai",
        "dich-vu",
        "phien-dich",
        "huong-dan-vien",
        "hanh-ly",
        "khach-san",
        "dat-phong",
        "visa",
        "ho-chieu",
        "dua-don",
        "san-bay",
        "don-tien",
        "bao-gom",
        "bua-an",
        "an-chay",
        "thu-cung",
        "wifi",
        "tre-em",
        "tre-nho",
        "do-tuoi",
        "mua-ve",
    }
    FAQ_QUERY_TAG_PATTERNS = {
        "food": {
            "an-gi",
            "mon-gi",
            "mon-an",
            "an-uong",
            "am-thuc",
            "dac-san",
            "ca-phe",
            "quan-ca-phe",
            "quan-an",
            "nha-hang",
            "phai-thu",
        },
        "weather": {
            "thoi-tiet",
            "khi-hau",
            "nang-khong",
            "mua-khong",
            "nhiet-do",
            "nong-khong",
            "lanh-khong",
            "ret-khong",
        },
        "clothing": {
            "mac-gi",
            "mac-do",
            "nen-mac",
            "trang-phuc",
            "quan-ao",
            "chuan-bi-gi",
            "mang-gi",
            "do-gi",
            "giay-dep",
            "ao-khoac",
        },
        "culture": {"van-hoa", "le-hoi", "lich-su", "phong-tuc", "tap-quan", "dan-toc"},
        "transport": {
            "phuong-tien",
            "di-chuyen",
            "di-lai",
            "cach-di",
            "den-bang-gi",
            "xe-khach",
            "may-bay",
            "tau-hoa",
            "tau-thuyen",
            "thue-xe",
        },
        "entertainment": {"choi-gi", "gi-choi", "gi-vui", "gi-hay", "tham-quan-gi", "check-in", "dia-diem"},
        "shopping": {"mua-gi", "mua-sam", "cho-dem", "cho-nao"},
        "famous destination": {"o-dau", "di-dau"},
        "service": {
            "ho-tro", "dich-vu", "phien-dich", "huong-dan-vien",
            "hanh-ly", "khach-san", "dat-phong", "dua-don", "san-bay",
            "don-tien", "bao-gom", "bua-an", "an-chay", "thu-cung", "wifi",
        },
        "tour_schedule_changes": {"doi-lich", "thay-doi-lich", "thay-doi", "rut-ngan"},
        "tour_cancellation_refund": {"huy-tour", "hoan-tien", "chinh-sach"},
        "tour_booking_conditions": {
            "dat-coc", "thu-tuc", "dieu-kien", "tre-em", "tre-nho",
            "do-tuoi", "mua-ve",
        },
        "tour_customer_support": {"khieu-nai", "ho-tro", "thu-cung", "wifi"},
        "payment": {"thanh-toan", "tra-gop", "dat-coc"},
        "visa": {"visa", "ho-chieu"},
    }
    FAQ_LOCATION_RELATED_TERMS = {
        "Đà Lạt": ("Lâm Đồng",),
        "Phú Quốc": ("Kiên Giang",),
        "Nha Trang": ("Khánh Hòa",),
        "Sa Pa": ("Lào Cai",),
        "Hạ Long": ("Quảng Ninh",),
        "Huế": ("Thừa Thiên Huế",),
        "Hội An": ("Quảng Nam",),
        "Quy Nhơn": ("Bình Định",),
        "Vũng Tàu": ("Bà Rịa Vũng Tàu", "Bà Rịa"),
        "Phan Thiết": ("Bình Thuận", "Mũi Né"),
        "TP HCM": ("Sài Gòn", "Hồ Chí Minh"),
        "Phong Nha": ("Quảng Bình",),
        "Côn Đảo": ("Bà Rịa Vũng Tàu",),
        "Cát Bà": ("Hải Phòng",),
        "Tam Đảo": ("Vĩnh Phúc",),
        "Mộc Châu": ("Sơn La",),
        "Mai Châu": ("Hòa Bình",),
        "Lý Sơn": ("Quảng Ngãi",),
    }
    EXPLICIT_TOUR_QUERY_PATTERNS = {
        "tour",
        "dat-tour",
        "tim-tour",
        "co-tour",
        "tu-van-tour",
        "lich-trinh",
        "khoi-hanh",
        "lich-khoi-hanh",
        "gia-tour",
        "book-tour",
    }
    SEARCH_REQUEST_KEYWORDS = {
        "tour",
        "du lịch",
        "đi chơi",
        "đi du",
        "muốn đi",
        "muốn tìm",
        "muốn book",
        "khởi hành",
        "ngân sách",
        "đặt tour",
        "book tour",
    }
    FAQ_CANDIDATE_QUERY_PATTERNS = {
        "co-nhung",
        "co-gi",
        "co-phai",
        "nen-ghe",
        "nen-di",
        "noi-tieng",
        "phai-thu",
        "phu-hop",
        "duoc-khong",
        "khong",
        "nao",
        "bao-nhieu",
    }
    FAQ_TERM_STOPWORDS = {
        "toi",
        "ban",
        "em",
        "anh",
        "chi",
        "co",
        "khong",
        "duoc",
        "the",
        "nao",
        "gi",
        "la",
        "ve",
        "tour",
        "guide",
        "di",
        "khi",
        "trong",
        "cua",
        "cho",
        "voi",
        "mot",
        "nhung",
        "cac",
        "neu",
        "muon",
    }
    FAQ_FOLLOWUP_PATTERNS = {
        "nhung",
        "nhung-ma",
        "vay",
        "the",
        "con",
        "luc-do",
        "khi-do",
        "mua-he",
        "mua-dong",
        "mua-mua",
        "mua-kho",
        "thang",
    }
    FAQ_TOPIC_HINTS = {
        "clothing": "mặc gì",
        "weather": "thời tiết",
        "food": "ăn gì",
        "famous destination": "nên đi đâu",
        "entertainment": "chơi gì",
        "shopping": "mua gì",
        "transport": "di chuyển",
        "culture": "văn hóa",
        "service": "dịch vụ",
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

    def extract_intent(self, query, user_id="default_user"):
        if self._should_continue_faq(query, user_id):
            return "out_of_scope"

        if self._should_route_to_faq(query):
            return "out_of_scope"

        if self.intent_tokenizer is None or self.intent_model is None:
            return self._extract_intent_fallback(query, user_id)

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
            intent = self.INTENT_LABELS.get(predicted_class, "out_of_scope")
            if intent == "out_of_scope" and self._looks_like_explicit_tour_query(query):
                return self._extract_intent_fallback(query, user_id)
            return intent
        except Exception as exc:
            logger.error("Intent classification failed: %s", exc)
            return self._extract_intent_fallback(query, user_id)

    def _extract_intent_fallback(self, query, user_id="default_user"):
        session = self.session_manager.get_session(user_id)
        has_location = bool(extract_destination_from_text(query)[1])
        has_time = extract_all_times(query) is not None
        has_price = extract_price_vn(query) is not None
        has_active_search_context = self._has_active_search_context(session)

        # Explicit tour keywords are the ONLY signal that should enter search.
        # A bare destination (e.g. "Hà Nội có phim gì") is NOT enough.
        has_tour_keyword = self._looks_like_search_request(query)
        # Bare budget snippets are useful search starts, but bare time snippets
        # should only continue an active search. This prevents FAQ follow-ups
        # like "nhưng tháng 5 là mùa hè mà" from becoming tour search.
        has_search_fragment = (
            (has_price or (has_time and has_active_search_context))
            and not has_location
        )
        has_location_completion = (
            has_location
            and not has_tour_keyword
            and has_active_search_context
            and not session.get("location")
        )

        if not has_tour_keyword and not has_search_fragment and not has_location_completion:
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

    @classmethod
    def _query_slug(cls, query: str) -> str:
        return slugify_vietnamese(query) or ""

    @classmethod
    def _contains_any_pattern(cls, query_slug: str, patterns: set[str]) -> bool:
        return any(pattern in query_slug for pattern in patterns)

    @classmethod
    def _looks_like_knowledge_query(cls, query: str) -> bool:
        return cls._contains_any_pattern(cls._query_slug(query), cls.KNOWLEDGE_QUERY_PATTERNS)

    @classmethod
    def _looks_like_service_query(cls, query: str) -> bool:
        return cls._contains_any_pattern(cls._query_slug(query), cls.SERVICE_QUERY_PATTERNS)

    @classmethod
    def _looks_like_explicit_tour_query(cls, query: str) -> bool:
        query_slug = cls._query_slug(query) or ""
        # "tour-guide" is the company brand name, not a tour search intent
        cleaned = query_slug.replace("tour-guide", "")
        return cls._contains_any_pattern(cleaned, cls.EXPLICIT_TOUR_QUERY_PATTERNS)

    @classmethod
    def _looks_like_search_request(cls, query: str) -> bool:
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in cls.SEARCH_REQUEST_KEYWORDS)

    @classmethod
    def _looks_like_travel_faq_candidate(cls, query: str) -> bool:
        query_slug = cls._query_slug(query)
        has_location = bool(extract_destination_from_text(query)[1])
        return has_location and cls._contains_any_pattern(
            query_slug,
            cls.FAQ_CANDIDATE_QUERY_PATTERNS,
        )

    @classmethod
    def _looks_like_faq_candidate(cls, query: str) -> bool:
        if cls._looks_like_service_query(query):
            return True
        if cls._looks_like_explicit_tour_query(query):
            return False
        return cls._looks_like_knowledge_query(query) or cls._looks_like_travel_faq_candidate(query)

    @classmethod
    def _should_route_to_faq(cls, query: str) -> bool:
        return cls._looks_like_faq_candidate(query)

    @staticmethod
    def _has_active_search_context(session: dict) -> bool:
        return bool(
            session.get("location")
            or session.get("time")
            or session.get("price")
            or session.get("search_history")
        )

    def _should_continue_faq(self, query: str, user_id: str) -> bool:
        context = self.session_manager.get_conversation_context(user_id)
        if context.get("last_mode") != "faq":
            return False
        if self._looks_like_search_request(query):
            return False
        if extract_price_vn(query) is not None:
            return False
        if self._looks_like_faq_candidate(query):
            return True

        query_slug = self._query_slug(query)
        has_time = extract_all_times(query) is not None
        has_followup_marker = self._contains_any_pattern(query_slug, self.FAQ_FOLLOWUP_PATTERNS)
        return bool(
            context.get("last_location")
            and context.get("last_topic")
            and (has_time or has_followup_marker)
        )

    def _build_contextual_faq_query(self, query: str, user_id: str) -> str:
        if not self._should_continue_faq(query, user_id):
            return query

        if self._faq_location_terms(query):
            return query

        context = self.session_manager.get_conversation_context(user_id)
        topic_hint = self.FAQ_TOPIC_HINTS.get(context.get("last_topic"))
        parts = [
            context.get("last_location"),
            topic_hint,
            query,
        ]
        return " ".join(part for part in parts if part)

    def _can_seed_location_from_context(
        self,
        query: str,
        intent: str,
        session: dict,
        context: dict,
    ) -> bool:
        if intent not in (self.LOCATION_INTENTS | self.TIME_INTENTS | self.PRICE_INTENTS):
            return False
        if session.get("location") or extract_destination_from_text(query)[1]:
            return False
        if not context.get("last_location"):
            return False
        if self._looks_like_explicit_tour_query(query):
            return True
        if self._looks_like_search_request(query) and extract_all_times(query) is not None:
            return True
        return self._has_active_search_context(session)

    def _update_conversation_context(
        self,
        user_id: str,
        query: str,
        mode: str,
        entities: Optional[ExtractedEntities] = None,
    ):
        session = self.session_manager.get_session(user_id)
        context = self.session_manager.get_conversation_context(user_id)

        location = entities.location if entities else None
        destination_normalized = entities.destination_normalized if entities else None
        if not location:
            location, destination_normalized = extract_destination_from_text(query)
        if location:
            location_switched = (
                mode == "faq"
                and session.get("location")
                and slugify_vietnamese(session.get("location")) != destination_normalized
            )
            context["last_location"] = location
            context["last_location_normalized"] = destination_normalized
            if location_switched:
                # An explicit knowledge question about another destination is a
                # topic switch. Clear stale search slots so follow-up tour
                # requests use the newer conversation context instead.
                context["last_time"] = None
                self.session_manager.reset_search_state(user_id)
                session = self.session_manager.get_session(user_id)

        raw_time = entities.time if entities else None
        if not raw_time:
            raw_time = extract_all_times(query)
        if raw_time:
            context["last_time"] = raw_time

        tags = sorted(self._faq_query_tags(query))
        if tags:
            context["last_topics"] = tags
            context["last_topic"] = tags[0]

        context["last_mode"] = mode
        context["last_query"] = query
        context["last_updated"] = datetime.now()
        session["last_updated"] = datetime.now()

    @classmethod
    def _faq_query_tags(cls, query: str) -> set[str]:
        query_slug = cls._query_slug(query)
        return {
            tag
            for tag, patterns in cls.FAQ_QUERY_TAG_PATTERNS.items()
            if cls._contains_any_pattern(query_slug, patterns)
        }

    @classmethod
    def _faq_query_terms(cls, text: str) -> set[str]:
        return {
            term
            for term in re.findall(r"[a-z0-9]+", cls._query_slug(text))
            if len(term) >= 3 and term not in cls.FAQ_TERM_STOPWORDS
        }

    @classmethod
    def _faq_season_terms(cls, text: str) -> set[str]:
        text_slug = cls._query_slug(text)
        terms = {
            season
            for season in {"mua-he", "mua-dong", "mua-mua", "mua-kho", "mua-thu", "mua-xuan"}
            if season in text_slug
        }
        for month in re.findall(r"thang-(\d{1,2})", text_slug):
            month_number = int(month)
            if 5 <= month_number <= 8:
                terms.add("mua-he")
            elif month_number in {11, 12, 1, 2}:
                terms.add("mua-dong")
            elif month_number in {9, 10}:
                terms.add("mua-thu")
            elif month_number in {3, 4}:
                terms.add("mua-xuan")
        return terms

    @classmethod
    def _faq_location_terms(cls, query: str) -> list[str]:
        location, _ = extract_destination_from_text(query)
        if not location:
            return []

        terms = [location, *cls.FAQ_LOCATION_RELATED_TERMS.get(location, ())]
        return list(dict.fromkeys(terms))

    @classmethod
    def _metadata_text_matches_terms(cls, text: str, terms: list[str]) -> bool:
        text_slug = cls._query_slug(text)
        return any(
            bool(term_slug) and term_slug in text_slug
            for term_slug in (cls._query_slug(term) for term in terms)
        )

    def _retrieve_faq_from_metadata(self, query: str, limit: int) -> list[FAQSource]:
        metadata = getattr(self.retrievalPipeline, "metadata", None)
        if not metadata:
            return []

        location_terms = self._faq_location_terms(query)
        query_tags = self._faq_query_tags(query)
        query_terms = self._faq_query_terms(query)
        query_season_terms = self._faq_season_terms(query)
        if not location_terms and not query_tags and not query_terms:
            return []

        candidates = []
        for idx, item in enumerate(metadata):
            question = item.get("question") or ""
            answer = item.get("answer") or ""
            tags = item.get("tags") or []
            searchable_text = f"{question} {answer} {' '.join(tags)}"

            location_matches = self._metadata_text_matches_terms(searchable_text, location_terms)
            normalized_tags = {str(tag).strip().lower() for tag in tags}
            tag_matches = query_tags.intersection(normalized_tags)
            term_matches = query_terms.intersection(self._faq_query_terms(searchable_text))
            season_matches = query_season_terms.intersection(self._faq_season_terms(searchable_text))

            score = 0.0
            if location_terms and location_matches:
                score += 3.0
            if tag_matches:
                score += 2.0 * len(tag_matches)
            if season_matches:
                score += 2.5 * len(season_matches)
            if term_matches:
                score += min(3.0, 0.5 * len(term_matches))

            # Require at least one match dimension
            if score == 0:
                continue
            # When both signals are available, require both to match
            if location_terms and query_tags and not (location_matches and tag_matches):
                continue
            # Avoid returning the first broad service result solely because it shares a tag
            if not location_terms and query_tags and not term_matches:
                continue

            candidates.append(
                (
                    score,
                    idx,
                    FAQSource(
                        question=question,
                        answer=answer,
                        tags=tags,
                        score=round(score / 5.0, 4),
                        source=f"faq_metadata_keyword:{idx}",
                    ),
                )
            )

        candidates.sort(key=lambda item: (-item[0], item[1]))
        return [source for _, _, source in candidates[:limit]]

    def extract_entities(self, query, intent, user_id="default_user"):
        session = self.session_manager.get_session(user_id)
        context = self.session_manager.get_conversation_context(user_id)
        location = session["location"]
        time = session["time"]
        price = session["price"]

        if self._can_seed_location_from_context(query, intent, session, context):
            location = context["last_location"]
            session["location"] = location
            logger.debug("Seeded location from conversation context=%s", location)

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

    def get_faq_response(self, query, k=3, user_id="default_user"):
        retrieval_query = self._build_contextual_faq_query(query, user_id)
        out_of_scope_message = (
            "Dạ, em chỉ hỗ trợ các câu hỏi liên quan đến du lịch hoặc tư vấn tour phù hợp. "
            "Mong bạn thông cảm."
        )
        retrieval_unavailable_message = (
            "Dạ, em chưa có thông tin chi tiết để trả lời câu hỏi này. "
            "Quý khách có thể hỏi về tour du lịch hoặc thử lại sau nhé."
        )
        is_knowledge = self._looks_like_knowledge_query(retrieval_query)
        is_service = self._looks_like_service_query(retrieval_query)
        is_faq_candidate = self._looks_like_faq_candidate(retrieval_query)
        fallback_message = (
            retrieval_unavailable_message if is_faq_candidate else out_of_scope_message
        )

        # If the query is location-dependent knowledge (NOT service) but no location
        # found, ask for clarification instead of returning irrelevant results
        location_terms = self._faq_location_terms(retrieval_query)
        query_tags = self._faq_query_tags(retrieval_query)
        if is_knowledge and not is_service and not location_terms and query_tags:
            return (
                "Dạ, quý khách muốn hỏi về địa điểm nào ạ? "
                "Ví dụ: Đà Lạt, Đà Nẵng, Nha Trang, Phú Quốc..."
            ), []

        if self.retrievalPipeline is None:
            return fallback_message, []

        # Non-knowledge, non-service queries should not fall through to FAISS
        if not is_faq_candidate:
            return fallback_message, []

        try:
            sources = self._retrieve_faq_from_metadata(retrieval_query, limit=k)
            if not sources:
                sources = self.retrievalPipeline.retrieve(retrieval_query, top_k=k)
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
        intent = self.extract_intent(query, user_id=user_id)
        logger.info("Detected intent=%s user_id=%s", intent, user_id)

        if intent == "out_of_scope":
            message, faq_sources = self.get_faq_response(query, user_id=user_id)
            faq_mode = (
                "faq"
                if faq_sources
                or self._looks_like_faq_candidate(self._build_contextual_faq_query(query, user_id))
                else "out_of_scope"
            )
            self._update_conversation_context(user_id, query, mode=faq_mode)
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
            self._update_conversation_context(user_id, query, mode="missing_info", entities=entities)
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
        self._update_conversation_context(user_id, query, mode=status, entities=entities)

        if status in {"success", "no_results"}:
            self.session_manager.reset_search_state(user_id)

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
            return fallback

        fallback = (
            f"Dạ, em đã ghi nhận điểm đến {entities.location}. "
            "Quý khách cho em xin thêm thời gian khởi hành hoặc ngân sách dự kiến để em bắt đầu tìm tour phù hợp."
        )
        return fallback

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
