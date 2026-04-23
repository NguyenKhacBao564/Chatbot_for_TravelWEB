from datetime import date

from schemas.tour_models import Tour, TourSearchFilters
from services.tour_search_service import TourSearchService


class FakeTourRepository:
    def list_tours(self):
        return [
            Tour(
                id="tour_dalat_match",
                name="Đà Lạt match",
                destination="Đà Lạt",
                destination_normalized="da-lat",
                departure_date=date(2026, 12, 12),
                price=4590000,
                url="/tour/tour_dalat_match",
                rating=4.5,
            ),
            Tour(
                id="tour_dalat_too_expensive",
                name="Đà Lạt expensive",
                destination="Đà Lạt",
                destination_normalized="da-lat",
                departure_date=date(2026, 12, 13),
                price=6590000,
                url="/tour/tour_dalat_too_expensive",
            ),
            Tour(
                id="tour_phuquoc",
                name="Phú Quốc",
                destination="Phú Quốc",
                destination_normalized="phu-quoc",
                departure_date=date(2026, 12, 12),
                price=4590000,
                url="/tour/tour_phuquoc",
            ),
        ]


def test_search_filters_destination_date_and_budget():
    service = TourSearchService(repository=FakeTourRepository())
    results = service.search(
        TourSearchFilters(
            destination="Đà Lạt",
            destination_normalized="da-lat",
            date_start=date(2026, 12, 1),
            date_end=date(2026, 12, 31),
            price_max=5000000,
        )
    )

    assert [tour.id for tour in results] == ["tour_dalat_match"]

