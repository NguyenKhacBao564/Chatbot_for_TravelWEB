import json
import logging
import os
from pathlib import Path
from typing import List, Protocol

from schemas.tour_models import Tour
from services.entity_normalizer import normalize_destination


logger = logging.getLogger(__name__)


class TourRepository(Protocol):
    """Read-only data access contract for tour search."""

    def list_tours(self) -> List[Tour]:
        ...


class JsonTourRepository:
    """Adapter for local tour data.

    Replace this adapter with a SQL/API implementation when the website database
    connection is available. The search service does not need to change.
    """

    def __init__(self, file_path: str | None = None):
        self.file_path = Path(file_path or os.getenv("TOUR_DATA_FILE", "data/tours_sample.json"))

    def list_tours(self) -> List[Tour]:
        if not self.file_path.exists():
            logger.warning("Tour data file not found: %s", self.file_path)
            return []

        with self.file_path.open("r", encoding="utf-8") as f:
            raw_tours = json.load(f)

        tours = []
        for item in raw_tours:
            tour_data = dict(item)
            if not tour_data.get("destination_normalized"):
                tour_data["destination_normalized"] = normalize_destination(
                    tour_data.get("destination")
                )[1]
            tours.append(Tour(**tour_data))
        return tours

