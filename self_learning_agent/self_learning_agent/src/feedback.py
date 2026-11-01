"""Turns thumbs up/down (+ optional comment) into a saved record AND a memory lesson."""
import logging

from src import database
from src.memory_manager import MemoryManager
from src.utils import contains_sensitive

logger = logging.getLogger(__name__)


def build_lesson(question: str, answer: str, rating: int, comment: str) -> str:
    q, a = question[:200], answer[:300]
    if rating < 0:
        base = f"User was NOT happy with a reply to a question like: '{q}'. "
        base += f"Their feedback: {comment}. " if comment else ""
        return base + f"Avoid answering in this style next time (the bad reply began: '{a[:120]}...')."
    base = f"User LIKED a reply to a question like: '{q}'. "
    base += f"Their comment: {comment}. " if comment else ""
    return base + f"Keep a similar style next time (the good reply began: '{a[:120]}...')."


def handle_feedback(memory: MemoryManager, message_id: int, rating: int, comment: str = "") -> str:
    """rating: +1 (good) or -1 (bad). Returns a short status message for the UI."""
    comment = (comment or "").strip()[:300]
    answer_msg = database.get_message(message_id)
    if not answer_msg:
        return "Could not find that message."
    database.save_feedback(message_id, rating, comment)

    question = database.get_previous_user_message(message_id)
    if contains_sensitive(question + comment):
        return "Feedback saved, but not added to memory (it looked sensitive)."
    try:
        memory.add_feedback_lesson(build_lesson(question, answer_msg["content"], rating, comment))
    except Exception as e:
        logger.exception("Could not store feedback lesson")
        return f"Feedback saved, but memory update failed: {e}"
    return "Thanks! Feedback saved and added to memory."
