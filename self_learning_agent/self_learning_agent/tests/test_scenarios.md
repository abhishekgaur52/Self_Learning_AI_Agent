# Manual test checklist (Streamlit UI)

| # | Step | Expected result |
|---|------|-----------------|
| 1 | Chat: "Remember that my name is Sam." | Friendly reply. |
| 2 | Memory Explorer | A memory like "Name is Sam" exists. |
| 3 | Stop the app (Ctrl+C) and run `streamlit run app.py` again | Old chat still in sidebar. |
| 4 | New conversation: "What is my name?" | Answers "Sam". Expander "Memories used" shows the name memory. |
| 5 | Ask "Explain what an API is." then Give feedback → comment "Too long, use 2 sentences" → 👎 | "Feedback saved" message. A [feedback] memory appears in Memory Explorer. |
| 6 | New conversation: "Explain what a database is." | Noticeably shorter answer; memories used includes the feedback lesson. |
| 7 | Memory Explorer: edit a memory, then delete one | Edit shows after reload; deleted memory disappears. |
| 8 | Send an empty message / 3000 characters | Friendly warning, no crash. |
| 9 | Send "my password is hunter2" | Reply works; warning that it was not saved to memory. |
