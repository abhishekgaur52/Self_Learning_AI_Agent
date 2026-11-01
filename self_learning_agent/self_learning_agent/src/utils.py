"""Small helpers: logging, input validation, and a simple sensitive-data filter."""
import logging
import re

from src.config import MAX_INPUT_CHARS


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def validate_user_input(text: str) -> str:
    """Return cleaned text or raise ValueError with a friendly message."""
    if text is None or not text.strip():
        raise ValueError("Please type a message.")
    text = text.strip()
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"Message is too long (max {MAX_INPUT_CHARS} characters).")
    return text


_SENSITIVE = [
    r"\b(?:\d[ -]?){13,16}\b",                       # card-like numbers
    r"\b\d{3}-\d{2}-\d{4}\b",                        # US SSN pattern
    r"\bAIza[0-9A-Za-z_\-]{20,}",                    # Google API keys
    r"\bsk-[A-Za-z0-9]{20,}",                        # other API keys
    r"(?i)\b(password|passcode|pin|cvv|otp)\b\s*(is|=|:)",
]


def contains_sensitive(text: str) -> bool:
    """True if text looks like it has secrets. We then skip saving it to memory."""
    return any(re.search(p, text) for p in _SENSITIVE)
