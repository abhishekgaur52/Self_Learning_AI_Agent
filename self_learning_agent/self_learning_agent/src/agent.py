"""The brain: retrieve memories -> build prompt -> ask Gemini -> save -> learn."""
import logging

from src import database
from src.config import GEMINI_MODEL, GOOGLE_API_KEY, HISTORY_TURNS, MEMORIES_TO_RETRIEVE
from src.gemini_client import GeminiClient
from src.memory_manager import MemoryManager
from src.utils import contains_sensitive, validate_user_input

logger = logging.getLogger(__name__)

SYSTEM_RULES = (
    "You are a helpful personal assistant with long-term memory.\n"
    "Use the memories below to personalize your answer, but only when they are relevant. "
    "Do not mention the word 'memory' unless asked. If a memory conflicts with what the "
    "user says now, trust the user's latest message.\n"
    "Follow the 'Lessons from feedback' closely: they describe what this user likes and dislikes."
)


class Agent:
    def __init__(self, memory: MemoryManager, gemini: GeminiClient | None = None):
        self.memory = memory
        self.gemini = gemini or GeminiClient(GOOGLE_API_KEY, GEMINI_MODEL)
        database.init_db()

    def _build_system_prompt(self, memories: list[dict]) -> str:
        facts = [m["memory"] for m in memories if m["metadata"].get("type") != "feedback"]
        lessons = [m["memory"] for m in memories if m["metadata"].get("type") == "feedback"]
        parts = [SYSTEM_RULES]
        parts.append("\nKnown facts about the user:\n" + ("\n".join(f"- {f}" for f in facts) or "- (none yet)"))
        parts.append("\nLessons from feedback:\n" + ("\n".join(f"- {l}" for l in lessons) or "- (none yet)"))
        return "\n".join(parts)

    def respond(self, conversation_id: int, user_text: str) -> dict:
        """Returns {"answer", "assistant_message_id", "memories", "warning"}. May raise ValueError/GeminiError."""
        user_text = validate_user_input(user_text)
        warning = None

        # 1) Retrieve relevant memories (a memory failure must not stop the chat)
        try:
            memories = self.memory.search(user_text, MEMORIES_TO_RETRIEVE)
        except Exception as e:
            logger.exception("Memory search failed")
            memories, warning = [], f"Memory search failed, answering without memories: {e}"

        # 2) Recent history + prompt, then ask Gemini
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in database.get_messages(conversation_id, limit=HISTORY_TURNS)
        ]
        answer = self.gemini.generate(self._build_system_prompt(memories), history, user_text)

        # 3) Save transcript
        is_first = not history
        database.add_message(conversation_id, "user", user_text)
        assistant_id = database.add_message(conversation_id, "assistant", answer, retrieved=memories)
        if is_first:
            database.rename_conversation(conversation_id, user_text)

        # 4) Learn: let Mem0 extract/update/delete facts (skip sensitive text)
        if contains_sensitive(user_text):
            warning = "That message looked sensitive, so it was not saved to memory."
        else:
            try:
                self.memory.add_conversation(user_text, answer)
            except Exception as e:
                logger.exception("Memory add failed")
                warning = f"Answer ok, but saving to memory failed: {e}"

        return {"answer": answer, "assistant_message_id": assistant_id, "memories": memories, "warning": warning}
