from datetime import date

from pipelines.tour_pipeline import TourRetrievalPipeline
from schemas.tour_models import Tour
from services.tour_search_service import TourSearchService


class FakeFAQPipeline:
    def retrieve(self, query, top_k=3):
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


def test_location_only_returns_missing_info_and_does_not_search():
    pipeline = build_pipeline()

    response = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_location_only")

    assert response["status"] == "missing_info"
    assert response["missing_fields"] == ["time", "price"]
    assert response["tours"] == []
    assert "thời gian" in response["message"]
    assert "ngân sách" in response["message"]


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


def test_sessions_are_still_isolated_by_user_id():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_a")
    second = pipeline.get_tour_response("Tôi muốn đi Phú Quốc", user_id="user_b")

    assert first["entities"]["destination_normalized"] == "da-lat"
    assert second["entities"]["destination_normalized"] == "phu-quoc"
    assert pipeline.session_manager.get_session("user_a")["location"] == "Đà Lạt"
    assert pipeline.session_manager.get_session("user_b")["location"] == "Phú Quốc"
