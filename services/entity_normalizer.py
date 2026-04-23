import calendar
import re
import unicodedata
from datetime import date
from typing import Optional, Tuple

from extractors.extract_price import extract_price_values
from schemas.tour_models import ExtractedEntities, TourSearchFilters


DESTINATION_ALIASES = {
    "da-lat": "Đà Lạt",
    "dalat": "Đà Lạt",
    "ha-noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "phu-quoc": "Phú Quốc",
    "nha-trang": "Nha Trang",
    "da-nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "sapa": "Sa Pa",
    "sa-pa": "Sa Pa",
    "ha-long": "Hạ Long",
    "hue": "Huế",
    "hoi-an": "Hội An",
    "ninh-binh": "Ninh Bình",
    "ha-giang": "Hà Giang",
    "quy-nhon": "Quy Nhơn",
    "vung-tau": "Vũng Tàu",
    "can-tho": "Cần Thơ",
}


def slugify_vietnamese(value: str | None) -> Optional[str]:
    if not value:
        return None
    value = value.replace("Đ", "D").replace("đ", "d").replace("_", " ")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or None


def normalize_destination(value: str | None) -> Tuple[Optional[str], Optional[str]]:
    slug = slugify_vietnamese(value)
    if not slug:
        return None, None

    slug = re.sub(r"^(tinh|thanh-pho|tp)-", "", slug)
    canonical = DESTINATION_ALIASES.get(slug, value.replace("_", " ").strip() if value else None)
    normalized = slugify_vietnamese(canonical)
    return canonical, normalized


def extract_destination_from_text(query: str) -> Tuple[Optional[str], Optional[str]]:
    query_slug = slugify_vietnamese(query) or ""
    for alias, canonical in sorted(DESTINATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in query_slug:
            return canonical, slugify_vietnamese(canonical)
    return None, None


def parse_time_range(raw_time: str | None) -> Tuple[Optional[date], Optional[date]]:
    if not raw_time:
        return None, None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_time):
        parsed = date.fromisoformat(raw_time)
        return parsed, parsed

    if re.fullmatch(r"\d{4}-\d{2}", raw_time):
        year, month = [int(part) for part in raw_time.split("-")]
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    return None, None


def parse_price_filter(query: str, raw_price: str | None) -> Tuple[Optional[int], Optional[int]]:
    prices = extract_price_values(query)
    range_hint = re.search(r"\b(tu|từ|den|đến|toi|tới)\b", query.lower())

    if len(prices) >= 2 and range_hint:
        return min(prices), max(prices)

    price = None
    if raw_price and str(raw_price).isdigit():
        price = int(raw_price)
    elif prices:
        price = max(prices)

    if price is None:
        return None, None

    lower_bound_hint = re.search(r"(trên|toi-thieu|tối thiểu|ít nhất|it nhat)", query.lower())
    if lower_bound_hint:
        return price, None

    return None, price


def normalize_entities(raw_entities: dict, query: str) -> ExtractedEntities:
    raw_location = raw_entities.get("location")
    location, destination_normalized = normalize_destination(raw_location)
    if not destination_normalized:
        location, destination_normalized = extract_destination_from_text(query)

    raw_time = raw_entities.get("time")
    raw_price = raw_entities.get("price")
    date_start, date_end = parse_time_range(raw_time)
    price_min, price_max = parse_price_filter(query, raw_price)

    return ExtractedEntities(
        location=location,
        time=raw_time,
        price=raw_price,
        destination_normalized=destination_normalized,
        date_start=date_start,
        date_end=date_end,
        price_min=price_min,
        price_max=price_max,
    )


def to_search_filters(entities: ExtractedEntities) -> TourSearchFilters:
    return TourSearchFilters(
        destination=entities.location,
        destination_normalized=entities.destination_normalized,
        date_start=entities.date_start,
        date_end=entities.date_end,
        price_min=entities.price_min,
        price_max=entities.price_max,
        raw_time=entities.time,
        raw_price=entities.price,
    )
