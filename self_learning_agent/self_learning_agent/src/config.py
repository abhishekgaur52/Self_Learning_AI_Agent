"""Central settings. Every other file imports from here, never from .env directly."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Must be set BEFORE mem0 is imported anywhere (turns off anonymous telemetry).
os.environ.setdefault("MEM0_TELEMETRY", "false")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIMS = int(os.getenv("EMBEDDING_DIMS", "768"))
USER_ID = os.getenv("MEMORY_USER_ID", "default_user")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SQLITE_PATH = str(DATA_DIR / "chat_history.db")
QDRANT_PATH = str(DATA_DIR / "mem0_qdrant")
MEM0_HISTORY_PATH = str(DATA_DIR / "mem0_history.db")

MAX_INPUT_CHARS = 2000      # longest message we accept
HISTORY_TURNS = 10          # recent messages sent to Gemini for context
MEMORIES_TO_RETRIEVE = 5    # memories fetched per question


def mem0_config() -> dict:
    """Mem0 settings: Gemini does the thinking AND the embeddings; Qdrant stores on disk."""
    return {
        "llm": {
            "provider": "gemini",
            "config": {
                "model": GEMINI_MODEL,
                "api_key": GOOGLE_API_KEY,
                "temperature": 0.1,
                "max_tokens": 1500,
            },
        },
        "embedder": {
            "provider": "gemini",
            "config": {
                "model": EMBEDDING_MODEL,
                "api_key": GOOGLE_API_KEY,
                "embedding_dims": EMBEDDING_DIMS,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "agent_memories",
                "path": QDRANT_PATH,
                "embedding_model_dims": EMBEDDING_DIMS,
                "on_disk": True,  # keeps memories after restart
            },
        },
        "history_db_path": MEM0_HISTORY_PATH,
    }
