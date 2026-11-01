# Self-Learning AI Agent (Gemini + Mem0 + Streamlit)

A chat agent that remembers you across restarts (Mem0), adapts from your feedback, and
shows exactly which memories it used. **Gemini is never retrained.**

## Memory vs feedback vs training
| Idea | What it does | In this app |
|---|---|---|
| Persistent memory | Saves facts outside the model and adds them to the prompt | Mem0 + local Qdrant in `data/` |
| Feedback adaptation | Saves "lessons" from 👍/👎 and retrieves them later | `src/feedback.py` -> Mem0 (`type: feedback`) |
| Model training | Changes the model's weights | **Not done** |

## Folder structure
```
app.py                  Streamlit UI (Chat, Memory Explorer, explanation page)
src/config.py           Settings and Mem0 config (reads .env)
src/utils.py            Input validation, sensitive-data filter, logging
src/gemini_client.py    Only file that calls Gemini (retries, friendly errors)
src/memory_manager.py   Only file that calls Mem0 (add/search/list/update/delete)
src/database.py         SQLite: chats, retrieved memories per answer, feedback
src/feedback.py         Converts feedback into saved lessons
src/agent.py            Orchestrates: retrieve -> prompt -> Gemini -> save -> learn
tests/smoke_test.py     Terminal tests (store / recall / feedback / manage)
tests/test_scenarios.md Manual UI checklist
data/                   Created at runtime (your memories and chats live here)
```

## Setup (Windows PowerShell)
```powershell
cd self_learning_agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env        # put your NEW Gemini key after GOOGLE_API_KEY=
```
Get a key at https://aistudio.google.com/app/apikey. Never share it or commit `.env`.

## Run
```powershell
streamlit run app.py
```
Open http://localhost:8501.

## Test
Terminal (close Streamlit first; local Mem0 storage allows one program at a time):
```powershell
python tests/smoke_test.py store      # "my name is Abhishek"
python tests/smoke_test.py recall     # new process = restart; should answer Abhishek
python tests/smoke_test.py feedback   # 👎 "too long", then a similar question
python tests/smoke_test.py manage     # update then delete a memory
```
UI checklist: `tests/test_scenarios.md`.

## Troubleshooting
- **Model not found / retired:** change `GEMINI_MODEL` in `.env`.
- **429 / rate limit:** wait a minute; the app already retries automatically.
- **"already accessed by another instance of Qdrant":** another Streamlit or test process is open. Close it.
- **Changed embedding model or EMBEDDING_DIMS:** delete the `data/mem0_qdrant` folder (old vectors have a different size).
- **PowerShell blocks activation:** `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
