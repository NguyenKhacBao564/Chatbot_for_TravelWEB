from datetime import date

from pipelines import tour_pipeline
from pipelines.tour_pipeline import TourRetrievalPipeline
from schemas.tour_models import Tour
from services.tour_search_service import TourSearchService


class FakeFAQPipeline:
    def __init__(self, metadata=None):
        self.calls = []
        self.metadata = metadata or []

    def retrieve(self, query, top_k=3):
        self.calls.append((query, top_k))
        return []


class FakeTourRepository:
    def list_tours(self):
        return [
            Tour(
                id="tour_dalat_december",
                name="Đà Lạt 3N2Đ",
                destination="Đà Lạt",
                destination_normalized="da-lat",
                departure_date=date(2026, 12, 12),
                price=4590000,
                url="/tour/tour_dalat_december",
            ),
            Tour(
                id="tour_dalat_january",
                name="Đà Lạt 4N3Đ",
                destination="Đà Lạt",
                destination_normalized="da-lat",
                departure_date=date(2026, 1, 10),
                price=4890000,
                url="/tour/tour_dalat_january",
            ),
            Tour(
                id="tour_phuquoc_december",
                name="Phú Quốc 3N2Đ",
                destination="Phú Quốc",
                destination_normalized="phu-quoc",
                departure_date=date(2026, 12, 18),
                price=4590000,
                url="/tour/tour_phuquoc_december",
            ),
        ]


def build_pipeline():
    return TourRetrievalPipeline(
        retrieval_pipeline=FakeFAQPipeline(),
        tour_search_service=TourSearchService(repository=FakeTourRepository()),
        load_models=False,
    )


def build_pipeline_with_faq_metadata(metadata):
    return TourRetrievalPipeline(
        retrieval_pipeline=FakeFAQPipeline(metadata=metadata),
        tour_search_service=TourSearchService(repository=FakeTourRepository()),
        load_models=False,
    )


def test_location_only_returns_missing_info_and_does_not_search():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_location_only")

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["time", "price"]
    assert response["tours"] == []
    assert "thời gian" in response["message"]
    assert "ngân sách" in response["message"]


def test_destination_food_question_routes_to_faq_without_polluting_session():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Đà Lạt có món gì", user_id="user_food_faq")

    assert response["status"] == "faq"
    assert response["entities"]["destination_normalized"] is None
    assert response["tours"] == []

    session = pipeline.session_manager.get_session("user_food_faq")
    assert session["location"] is None
    assert session["time"] is None
    assert session["price"] is None
    assert session["search_history"] == []


def test_destination_clothing_question_routes_to_faq_without_polluting_session():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("đà lạt thường mặc đồ gì", user_id="user_clothing_faq")

    assert response["status"] == "faq"
    assert response["entities"]["destination_normalized"] is None
    assert response["tours"] == []

    session = pipeline.session_manager.get_session("user_clothing_faq")
    assert session["location"] is None
    assert session["time"] is None
    assert session["price"] is None
    assert session["search_history"] == []


def test_destination_weather_question_routes_to_faq_without_polluting_session():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Thời tiết đà lạt ngày mai nắng không",
        user_id="user_weather_faq",
    )

    assert response["status"] == "faq"
    assert response["entities"]["destination_normalized"] is None
    assert response["tours"] == []

    session = pipeline.session_manager.get_session("user_weather_faq")
    assert session["location"] is None
    assert session["time"] is None
    assert session["price"] is None
    assert session["search_history"] == []


def test_knowledge_turn_does_not_seed_later_budget_search():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response("Đà Lạt có món gì", user_id="user_faq_then_budget")
    second = pipeline.get_tour_response("tài chính 3 tr", user_id="user_faq_then_budget")

    assert first["status"] == "faq"
    assert second["status"] == "missing_info"
    assert second["missing_fields"] == ["location"]
    assert second["tours"] == []
    assert second["entities"]["destination_normalized"] is None
    assert second["entities"]["price_max"] == 3000000


def test_explicit_tour_query_with_food_words_still_uses_search_flow():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Có tour nào Đà Lạt ăn uống ngon không",
        user_id="user_hybrid_tour_food",
    )

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["time", "price"]
    assert response["entities"]["destination_normalized"] == "da-lat"


def test_faq_fallback_for_travel_knowledge_query_is_contextual():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Đà Lạt có món gì ngon", user_id="user_faq_fallback")

    assert response["status"] == "faq"
    assert "chưa có thông tin" in response["message"] or "địa điểm nào" in response["message"]
    assert "chỉ hỗ trợ" not in response["message"]


def test_faq_fallback_for_non_travel_query_remains_out_of_scope():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Ai là tổng thống Mỹ", user_id="user_non_travel")

    assert response["status"] == "faq"
    assert "chỉ hỗ trợ" in response["message"]


def test_faq_metadata_keyword_search_prefers_matching_location_and_tag(monkeypatch):
    pipeline = build_pipeline_with_faq_metadata(
        [
            {
                "question": "Ngoài các món ăn đã kể trên, Tuyên Quang còn món gì độc đáo không?",
                "answer": "Bạn có thể thử xôi ngũ sắc ở Tuyên Quang.",
                "tags": ["food"],
            },
            {
                "question": "Đặc sản ẩm thực nào của Lâm Đồng mà du khách nên thử nhất?",
                "answer": "Lâm Đồng nổi tiếng với lẩu gà lá é, bánh căn Đà Lạt và dâu tây.",
                "tags": ["food"],
            },
        ]
    )

    monkeypatch.setattr(
        tour_pipeline,
        "get_genai_response",
        lambda prompt, fallback=None: fallback,
    )

    response = pipeline.get_tour_response("Đà Lạt có món gì ngon", user_id="user_faq_keyword")

    assert response["status"] == "faq"
    assert "lẩu gà lá é" in response["message"]
    assert response["faq_sources"][0]["source"] == "faq_metadata_keyword:1"
    assert pipeline.retrievalPipeline.calls == []


def test_cafe_recommendation_question_routes_to_faq_and_uses_metadata(monkeypatch):
    pipeline = build_pipeline_with_faq_metadata(
        [
            {
                "question": "Tuyên Quang có quán cà phê nào nổi tiếng?",
                "answer": "Tuyên Quang có một số quán cà phê trung tâm.",
                "tags": ["food"],
            },
            {
                "question": "Hà Nội có những quán cà phê nổi tiếng nào nên ghé thăm?",
                "answer": "Hà Nội có The Note Coffee, Cafe Giảng và nhiều quán cà phê phố cổ.",
                "tags": ["food"],
            },
        ]
    )
    monkeypatch.setattr(tour_pipeline, "get_genai_response", lambda prompt, fallback=None: fallback)

    response = pipeline.get_tour_response(
        "Hà Nội có những quán cà phê nổi tiếng nào nên ghé thăm?",
        user_id="user_hanoi_cafe",
    )

    assert response["status"] == "faq"
    assert "Cafe Giảng" in response["message"]
    assert response["faq_sources"][0]["source"] == "faq_metadata_keyword:1"
    assert response["tours"] == []
    assert pipeline.session_manager.get_session("user_hanoi_cafe")["search_history"] == []


def test_pet_policy_with_tour_word_routes_to_faq_not_search(monkeypatch):
    pipeline = build_pipeline_with_faq_metadata(
        [
            {
                "question": "Tôi có thể mang theo thú cưng trong tour không?",
                "answer": "Rất tiếc, hầu hết các tour không cho phép mang theo thú cưng.",
                "tags": ["tour_customer_support"],
            }
        ]
    )
    monkeypatch.setattr(tour_pipeline, "get_genai_response", lambda prompt, fallback=None: fallback)

    response = pipeline.get_tour_response(
        "Tôi có thể mang theo thú cưng khi đi tour không?",
        user_id="user_pet_policy",
    )

    assert response["status"] == "faq"
    assert "thú cưng" in response["message"]
    assert response["tours"] == []
    assert pipeline.session_manager.get_session("user_pet_policy")["search_history"] == []


def test_wifi_service_question_routes_to_contextual_faq_without_search():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Tour có wifi trên xe không?", user_id="user_wifi")

    assert response["status"] == "faq"
    assert "chỉ hỗ trợ" not in response["message"]
    assert response["tours"] == []
    assert pipeline.session_manager.get_session("user_wifi")["search_history"] == []


def test_child_ticket_question_does_not_parse_age_as_budget_or_pollute_session():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response(
        "Trẻ em dưới 5 tuổi có phải mua vé không?",
        user_id="user_child_ticket",
    )
    second = pipeline.get_tour_response("3tr", user_id="user_child_ticket")

    assert first["status"] == "faq"
    assert "ngân sách" not in first["message"]
    assert first["entities"]["price_max"] is None
    assert first["tours"] == []

    session = pipeline.session_manager.get_session("user_child_ticket")
    assert session["location"] is None
    assert session["time"] is None
    assert session["price"] == "3000000"

    assert second["status"] == "missing_info"
    assert second["missing_fields"] == ["location"]
    assert second["entities"]["price_max"] == 3000000


def test_location_and_time_runs_partial_search():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi Đà Lạt tháng 12 năm 2026",
        user_id="user_location_time",
    )

    assert response["status"] == "partial_search"
    assert response["missing_fields"] == ["price"]
    assert response["entities"]["destination_normalized"] == "da-lat"
    assert response["entities"]["date_start"] == "2026-12-01"
    assert response["entities"]["date_end"] == "2026-12-31"
    assert response["tours"][0]["id"] == "tour_dalat_december"


def test_location_and_price_runs_partial_search():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi Đà Lạt khoảng 5 triệu",
        user_id="user_location_price",
    )

    assert response["status"] == "partial_search"
    assert response["missing_fields"] == ["time"]
    assert response["entities"]["destination_normalized"] == "da-lat"
    assert response["entities"]["price_max"] == 5000000
    assert {tour["id"] for tour in response["tours"]} == {
        "tour_dalat_december",
        "tour_dalat_january",
    }


def test_full_search_with_location_time_and_price_still_returns_success():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi Đà Lạt tháng 12 năm 2026 khoảng 5 triệu",
        user_id="user_success",
    )

    assert response["status"] == "success"
    assert response["entities"]["destination_normalized"] == "da-lat"
    assert response["entities"]["date_start"] == "2026-12-01"
    assert response["entities"]["date_end"] == "2026-12-31"
    assert response["entities"]["price_max"] == 5000000
    assert response["missing_fields"] == []
    assert response["tours"][0]["id"] == "tour_dalat_december"


def test_full_no_results_resets_session():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi Đà Lạt tháng 12 năm 2026 khoảng 3 triệu",
        user_id="user_full_no_results",
    )

    assert response["status"] == "no_results"
    assert response["missing_fields"] == []
    assert response["tours"] == []

    session = pipeline.session_manager.get_session("user_full_no_results")
    assert session["location"] is None
    assert session["time"] is None
    assert session["price"] is None


def test_missing_info_message_does_not_call_gemini(monkeypatch):
    pipeline = build_pipeline()

    def fail_genai_call(prompt, fallback=None):
        raise AssertionError("missing_info should use deterministic fallback text")

    monkeypatch.setattr(tour_pipeline, "get_genai_response", fail_genai_call)

    response = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_no_gemini_missing")

    assert response["status"] == "missing_info"
    assert "thời gian" in response["message"]
    assert "ngân sách" in response["message"]


def test_time_only_returns_missing_location():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Tôi muốn đi tháng 12 năm 2026", user_id="user_time_only")

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["location"]
    assert response["tours"] == []
    assert "điểm đến" in response["message"]


def test_price_only_returns_missing_location():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Tôi muốn đi khoảng 5 triệu", user_id="user_price_only")

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["location"]
    assert response["tours"] == []
    assert "điểm đến" in response["message"]


def test_time_and_price_without_location_returns_missing_location():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi tháng 12 năm 2026 khoảng 5 triệu",
        user_id="user_time_price_only",
    )

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["location"]
    assert response["tours"] == []
    assert "điểm đến" in response["message"]


def test_partial_search_no_results_keeps_missing_optional_filter_visible():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tôi muốn đi Đà Lạt khoảng 3 triệu",
        user_id="user_partial_no_results",
    )

    assert response["status"] == "partial_search"
    assert response["missing_fields"] == ["time"]
    assert response["tours"] == []
    assert "thời gian" in response["message"]


def test_partial_search_preserves_session_until_full_search_completes():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_progress")
    second = pipeline.get_tour_response("tháng 12 năm 2026", user_id="user_progress")

    assert first["status"] == "missing_info"
    assert first["missing_fields"] == ["time", "price"]

    assert second["status"] == "partial_search"
    assert second["missing_fields"] == ["price"]
    assert second["tours"][0]["id"] == "tour_dalat_december"

    session_after_partial = pipeline.session_manager.get_session("user_progress")
    assert session_after_partial["location"] == "Đà Lạt"
    assert session_after_partial["time"] == "2026-12"

    third = pipeline.get_tour_response("khoảng 5 triệu", user_id="user_progress")

    assert third["status"] == "success"
    assert third["missing_fields"] == []
    assert third["tours"][0]["id"] == "tour_dalat_december"

    session_after_success = pipeline.session_manager.get_session("user_progress")
    assert session_after_success["location"] is None
    assert session_after_success["time"] is None
    assert session_after_success["price"] is None


def test_movie_question_routes_to_faq_not_tour_search():
    """Screenshot bug: 'Tối nay Hà Nội có phim gì hay không' was routed to tour search."""
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Tối nay Hà Nội có phim gì hay không", user_id="user_movie"
    )

    assert response["status"] == "faq"
    assert response["tours"] == []

    session = pipeline.session_manager.get_session("user_movie")
    assert session["location"] is None


def test_nghe_an_motorbike_question_routes_to_faq():
    """Screenshot bug: 'thuê xe máy khám phá Nghệ An' was misrouted to tour
    search with location=Huế because 'thue' slug contained 'hue' substring."""
    pipeline = build_pipeline()

    response = pipeline.get_tour_response(
        "Nếu muốn tự thuê xe máy để khám phá Nghệ An Tour Guide có hỗ trợ không",
        user_id="user_nghe_an",
    )

    assert response["status"] == "faq"
    assert response["tours"] == []
    assert response["entities"]["destination_normalized"] is None

    session = pipeline.session_manager.get_session("user_nghe_an")
    assert session["location"] is None


def test_generic_destination_question_without_tour_keyword_routes_to_faq():
    """Any destination + non-tour question should go to FAQ, not tour search."""
    pipeline = build_pipeline()

    for query in [
        "Hà Nội có lễ hội gì đặc sắc",
        "Nha Trang ăn hải sản ở đâu ngon",
        "Đà Nẵng có chỗ mua sắm nào",
        "Phú Quốc có gì vui",
    ]:
        response = pipeline.get_tour_response(query, user_id=f"user_{hash(query)}")
        assert response["status"] == "faq", f"'{query}' should be faq, got {response['status']}"
        assert response["tours"] == []


def test_sessions_are_still_isolated_by_user_id():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_a")
    second = pipeline.get_tour_response("Tôi muốn đi Phú Quốc", user_id="user_b")

    assert first["entities"]["destination_normalized"] == "da-lat"
    assert second["entities"]["destination_normalized"] == "phu-quoc"
    assert pipeline.session_manager.get_session("user_a")["location"] == "Đà Lạt"
    assert pipeline.session_manager.get_session("user_b")["location"] == "Phú Quốc"
