import logging
import os
from functools import lru_cache
from typing import Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Bạn là một trợ lý ảo thông minh của một công ty du lịch, hãy trả lời câu hỏi "
    "của người dùng một cách tự nhiên, chính xác và chuyên nghiệp."
)


@lru_cache(maxsize=1)
def _get_client():
    if genai is None:
        raise RuntimeError("google-genai is not installed")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    return genai.Client(api_key=api_key)


def get_genai_response(prompt: str, fallback: Optional[str] = None) -> str:
    """Generate natural language text with Gemini.

    Business-critical filtering should happen before this function is called.
    If Gemini is not configured or fails, callers get a deterministic fallback.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            contents=prompt,
        )
        return (response.text or "").replace("\n", " ").strip()
    except Exception as exc:
        logger.warning("Gemini response generation failed: %s", exc)
        return fallback or ""
