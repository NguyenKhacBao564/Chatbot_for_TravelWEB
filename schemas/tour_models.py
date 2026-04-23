from datetime import date
from typing import Optional

from pydantic import BaseModel


class Tour(BaseModel):
    id: str
    name: str
    destination: str
    destination_normalized: str
    departure_date: date
    price: int
    url: str
    duration_days: Optional[int] = None
    rating: Optional[float] = None
    popularity: Optional[int] = None


class TourSearchFilters(BaseModel):
    destination: Optional[str] = None
    destination_normalized: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    raw_time: Optional[str] = None
    raw_price: Optional[str] = None


class ExtractedEntities(BaseModel):
    location: Optional[str] = None
    time: Optional[str] = None
    price: Optional[str] = None
    destination_normalized: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None

