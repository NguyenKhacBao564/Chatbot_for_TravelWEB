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
                id="tour_dalat_001",
                name="Đà Lạt 3N2Đ",
                destination="Đà Lạt",
                destination_normalized="da-lat",
                departure_date=date(2026, 12, 12),
                price=4590000,
                url="/tour/tour_dalat_001",
            )
        ]


def build_pipeline():
    return TourRetrievalPipeline(
        retrieval_pipeline=FakeFAQPipeline(),
        tour_search_service=TourSearchService(repository=FakeTourRepository()),
        load_models=False,
    )


def test_successful_tour_search_flow_returns_structured_tours():
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
    assert response["tours"][0]["id"] == "tour_dalat_001"


def test_sessions_are_isolated_by_user_id():
    pipeline = build_pipeline()

    first = pipeline.get_tour_response("Tôi muốn đi Đà Lạt", user_id="user_a")
    second = pipeline.get_tour_response("Tôi muốn đi Phú Quốc", user_id="user_b")

    assert first["entities"]["destination_normalized"] == "da-lat"
    assert second["entities"]["destination_normalized"] == "phu-quoc"
    assert pipeline.session_manager.get_session("user_a")["location"] == "Đà Lạt"
    assert pipeline.session_manager.get_session("user_b")["location"] == "Phú Quốc"
