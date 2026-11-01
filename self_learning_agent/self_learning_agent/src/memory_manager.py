"""The ONLY file that talks to Mem0. Wraps add / search / list / update / delete."""
import logging

from src import config  # noqa: F401  (must import before mem0: sets telemetry env)
from mem0 import Memory

logger = logging.getLogger(__name__)


def _normalize(res) -> list[dict]:
    """Mem0 returns {"results": [...]}. Convert to a clean list of dicts."""
    items = res.get("results", []) if isinstance(res, dict) else (res or [])
    return [
        {
            "id": r.get("id"),
            "memory": r.get("memory", ""),
            "score": r.get("score"),
            "metadata": r.get("metadata") or {},
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }
        for r in items
    ]


class MemoryManager:
    def __init__(self, user_id: str = config.USER_ID):
        self.user_id = user_id
        self.mem = Memory.from_config(config.mem0_config())

    def add_conversation(self, user_text: str, assistant_text: str) -> list[dict]:
        """Mem0 uses Gemini to pick out useful facts, and to add/update/delete old ones."""
        messages = [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
        res = self.mem.add(messages, user_id=self.user_id, metadata={"type": "fact"})
        return _normalize(res)

    def add_feedback_lesson(self, lesson: str) -> None:
        """Stored exactly as written (infer=False) so feedback is never dropped."""
        self.mem.add(
            [{"role": "user", "content": lesson}],
            user_id=self.user_id,
            metadata={"type": "feedback"},
            infer=False,
        )

    def search(self, query: str, limit: int = config.MEMORIES_TO_RETRIEVE) -> list[dict]:
        res = self.mem.search(query, top_k=limit, filters={"user_id": self.user_id})
        return _normalize(res)

    def get_all(self, limit: int = 200) -> list[dict]:
        res = self.mem.get_all(filters={"user_id": self.user_id}, top_k=limit)
        return _normalize(res)

    def update(self, memory_id: str, new_text: str) -> None:
        self.mem.update(memory_id, text=new_text)

    def delete(self, memory_id: str) -> None:
        self.mem.delete(memory_id)
