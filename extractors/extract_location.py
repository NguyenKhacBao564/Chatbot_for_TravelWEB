import logging
import re
from typing import Optional


logger = logging.getLogger(__name__)


# Administrative prefixes to strip before matching
_ADMIN_PREFIXES = re.compile(
    r"^(tỉnh|thành\s*phố|tp\.?|huyện|quận|thị\s*xã)\s+",
    re.IGNORECASE,
)


def extract_location(query: str) -> Optional[str]:
    """Extract a location name from the query using alias-based matching.

    Delegates to the canonical alias extractor in entity_normalizer.
    Returns the canonical destination name or None.
    """
    if not query or not isinstance(query, str):
        return None

    from services.entity_normalizer import extract_destination_from_text

    canonical, _ = extract_destination_from_text(query)
    if canonical:
        return canonical

    return None
