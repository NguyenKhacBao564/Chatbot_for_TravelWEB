from datetime import date
from typing import List

from repositories.tour_repository import JsonTourRepository, TourRepository
from schemas.tour_models import Tour, TourSearchFilters


class TourSearchService:
    """Deterministic tour search over structured tour data."""

    def __init__(self, repository: TourRepository | None = None):
        self.repository = repository or JsonTourRepository()

    def search(self, filters: TourSearchFilters, limit: int = 5) -> List[Tour]:
        scored_results = []
        for tour in self.repository.list_tours():
            if not self._matches(tour, filters):
                continue
            scored_results.append((self._score(tour, filters), tour))

        scored_results.sort(
            key=lambda item: (-item[0], item[1].departure_date, item[1].price)
        )
        return [tour for _, tour in scored_results[:limit]]

    def _matches(self, tour: Tour, filters: TourSearchFilters) -> bool:
        if filters.destination_normalized:
            if tour.destination_normalized != filters.destination_normalized:
                return False

        if filters.date_start and filters.date_end:
            if not filters.date_start <= tour.departure_date <= filters.date_end:
                return False

        if filters.price_min is not None and tour.price < filters.price_min:
            return False

        if filters.price_max is not None and tour.price > filters.price_max:
            return False

        return True

    def _score(self, tour: Tour, filters: TourSearchFilters) -> float:
        score = 0.0
        if filters.destination_normalized and tour.destination_normalized == filters.destination_normalized:
            score += 50

        if filters.date_start and filters.date_end:
            score += self._date_score(tour.departure_date, filters.date_start, filters.date_end)

        if filters.price_max:
            score += max(0.0, 25 * (1 - abs(filters.price_max - tour.price) / filters.price_max))

        if tour.rating:
            score += min(tour.rating, 5) * 2

        if tour.popularity:
            score += min(tour.popularity, 100) / 20

        return score

    @staticmethod
    def _date_score(departure_date: date, date_start: date, date_end: date) -> float:
        if date_start == date_end:
            return 25 if departure_date == date_start else 0

        midpoint = date_start.toordinal() + (date_end.toordinal() - date_start.toordinal()) / 2
        distance = abs(departure_date.toordinal() - midpoint)
        window = max(1, date_end.toordinal() - date_start.toordinal())
        return max(0.0, 25 * (1 - distance / window))

