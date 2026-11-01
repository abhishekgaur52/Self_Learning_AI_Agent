"""Streamlit UI. Run with:  streamlit run app.py
Three pages: Chat, Memory Explorer, How learning works."""
import streamlit as st

from src.config import GOOGLE_API_KEY, GEMINI_MODEL, USER_ID  # config first (sets env vars)
from src import database
from src.agent import Agent
from src.feedback import handle_feedback
from src.gemini_client import GeminiError
from src.memory_manager import MemoryManager
from src.utils import setup_logging

st.set_page_config(page_title="Self-Learning AI Agent", page_icon="🧠", layout="wide")

if not GOOGLE_API_KEY:
    st.error("GOOGLE_API_KEY not found. Copy .env.example to .env and add your key, then restart.")
    st.stop()


@st.cache_resource(show_spinner="Starting agent...")
def get_services():
    """Created once per app run (Qdrant local storage allows only one open connection)."""
    setup_logging()
    database.init_db()
    memory = MemoryManager()
    return memory, Agent(memory)


try:
    memory, agent = get_services()
except Exception as e:
    st.error(f"Could not start the agent: {e}")
    st.stop()

st.session_state.setdefault("conv_id", None)
st.session_state.setdefault("flash", None)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("AI Agent")
    page = st.radio("Page", ["💬 Chat", "🧠 Memory Explorer", "ℹ️ How learning works"], label_visibility="collapsed")
    st.caption(f"Model: {GEMINI_MODEL} · User: {USER_ID}")
    if st.button("➕ New conversation", use_container_width=True):
        st.session_state.conv_id = None
        st.rerun()
    st.divider()
    st.subheader("Chat history")
    for c in database.list_conversations()[:20]:
        label = ("▶ " if c["id"] == st.session_state.conv_id else "") + (c["title"] or "New chat")[:30]
        if st.button(label, key=f"conv{c['id']}", use_container_width=True):
            st.session_state.conv_id = c["id"]
            st.rerun()


def show_memories(mems: list[dict]):
    if not mems:
        st.caption("No memories were retrieved.")
    for m in mems:
        kind = m["metadata"].get("type", "fact")
        score = f" (match {m['score']:.2f})" if m.get("score") is not None else ""
        st.markdown(f"- **[{kind}]** {m['memory']}{score}")


# ---------------- Chat page ----------------
if page == "💬 Chat":
    st.header("Chat")
    conv_id = st.session_state.conv_id

    if conv_id:
        for msg in database.get_messages(conv_id):
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant":
                    with st.expander(f"Memories used for this answer ({len(msg['retrieved_memories'])})"):
                        show_memories(msg["retrieved_memories"])
                    if msg["rating"] is not None:
                        st.caption("You rated this: " + ("👍 good" if msg["rating"] > 0 else "👎 bad"))
                    else:
                        with st.expander("Give feedback"):
                            comment = st.text_input("Optional comment (e.g. 'too long')", key=f"c{msg['id']}")
                            b1, b2 = st.columns(2)
                            rating = 1 if b1.button("👍 Good", key=f"up{msg['id']}") else (
                                -1 if b2.button("👎 Bad", key=f"down{msg['id']}") else 0)
                            if rating:
                                st.session_state.flash = ("success", handle_feedback(memory, msg["id"], rating, comment))
                                st.rerun()
    else:
        st.info("Start a new conversation below.")

    if st.session_state.flash:
        kind, text = st.session_state.flash
        getattr(st, kind)(text)
        st.session_state.flash = None

    prompt = st.chat_input("Ask me anything...")
    if prompt:
        try:
            if st.session_state.conv_id is None:
                st.session_state.conv_id = database.create_conversation()
            with st.spinner("Thinking..."):
                result = agent.respond(st.session_state.conv_id, prompt)
            if result["warning"]:
                st.session_state.flash = ("warning", result["warning"])
            st.rerun()
        except ValueError as e:
            st.warning(str(e))
        except GeminiError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# ---------------- Memory Explorer ----------------
elif page == "🧠 Memory Explorer":
    st.header("Memory Explorer")
    tab1, tab2 = st.tabs(["Saved memories", "Memories used per response"])

    with tab1:
        query = st.text_input("Search memories (leave empty to list all)")
        try:
            mems = memory.search(query.strip(), 20) if query.strip() else memory.get_all()
        except Exception as e:
            st.error(f"Could not load memories: {e}")
            mems = []
        st.caption(f"{len(mems)} memories")
        for m in mems:
            with st.container(border=True):
                kind = m["metadata"].get("type", "fact")
                st.markdown(f"**[{kind}]** {m['memory']}")
                st.caption(f"id: {m['id']} · created: {m['created_at']} · updated: {m['updated_at']}")
                c1, c2 = st.columns([4, 1])
                new_text = c1.text_input("Edit", value=m["memory"], key=f"edit{m['id']}", label_visibility="collapsed")
                if c1.button("💾 Save edit", key=f"save{m['id']}") and new_text.strip() and new_text != m["memory"]:
                    try:
                        memory.update(m["id"], new_text.strip())
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
                if c2.button("🗑️ Delete", key=f"del{m['id']}"):
                    try:
                        memory.delete(m["id"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

    with tab2:
        convs = database.list_conversations()
        if not convs:
            st.info("No conversations yet.")
        else:
            conv = st.selectbox("Conversation", convs, format_func=lambda c: f"#{c['id']} {c['title']}")
            answers = [m for m in database.get_messages(conv["id"]) if m["role"] == "assistant"]
            if answers:
                ans = st.selectbox("Answer", answers, format_func=lambda m: f"#{m['id']} {m['content'][:60]}...")
                show_memories(ans["retrieved_memories"])

# ---------------- Explanation page ----------------
else:
    st.header("How this agent 'learns'")
    st.markdown(
        """
**1. Persistent memory.** Facts like "my name is Sam" are saved by Mem0 on your disk and
added to each prompt. The model itself does not change.

**2. Feedback-based adaptation.** Your 👍/👎 and comments become saved "lessons".
They are retrieved for similar questions and tell Gemini what you like or dislike.

**3. Real model training.** This would change Gemini's weights (fine-tuning). **This app does
not do that.** Gemini is exactly the same model before and after you use the app.
        """
    )
