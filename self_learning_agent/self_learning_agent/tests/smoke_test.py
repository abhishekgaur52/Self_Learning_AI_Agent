"""Terminal test of the agent (no UI). Run each phase as a SEPARATE command.
Close Streamlit first: Mem0's local storage can only be opened by one program at a time.

  python tests/smoke_test.py store     # tell the agent your name
  python tests/smoke_test.py recall    # new process = a "restart"; asks for your name
  python tests/smoke_test.py feedback  # ask, give 👎, ask something similar
  python tests/smoke_test.py manage    # list, update, delete a memory
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import database  # noqa: E402
from src.agent import Agent  # noqa: E402
from src.feedback import handle_feedback  # noqa: E402
from src.memory_manager import MemoryManager  # noqa: E402


def ask(agent, conv, text):
    print(f"\nYOU: {text}")
    r = agent.respond(conv, text)
    print(f"AGENT: {r['answer']}")
    print("MEMORIES USED:", [m["memory"] for m in r["memories"]])
    if r["warning"]:
        print("WARNING:", r["warning"])
    return r


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    mem = MemoryManager()
    agent = Agent(mem)
    database.init_db()
    conv = database.create_conversation(f"test-{phase}")

    if phase == "store":
        ask(agent, conv, "Hi! Please remember that my name is Priya.")
        print("\nSTORED MEMORIES:", [m["memory"] for m in mem.get_all()])
    elif phase == "recall":
        ask(agent, conv, "What is my name?")
    elif phase == "feedback":
        r = ask(agent, conv, "Explain what an API is.")
        print(handle_feedback(mem, r["assistant_message_id"], -1, "Too long. Answer in 2 short sentences."))
        ask(agent, conv, "Explain what a database is.")
    elif phase == "manage":
        mems = mem.get_all()
        for m in mems:
            print(m["id"], "|", m["memory"])
        if mems:
            mem.update(mems[0]["id"], "The user's name is Priya Sharma.")
            print("Updated ->", [m["memory"] for m in mem.get_all()])
            mem.delete(mems[0]["id"])
            print("After delete ->", [m["memory"] for m in mem.get_all()])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
