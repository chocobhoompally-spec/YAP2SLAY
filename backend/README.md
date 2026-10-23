# Backend guide

`db.py` owns SQLite persistence and the UI-facing reads. `scheduler.py` is a pure deterministic 30-minute scheduler. `scheduler_service.py` validates inputs, rebuilds future blocks while preserving past history, and records operations. `tools.py` exposes those operations as Gemini-callable Python functions. `assistant.py` holds the Gemini chat wrapper and returns `{reply, actions}`; absent credentials or service failures produce an honest fallback.

The SQLite database is local and configured through `DB_PATH`. Set `GEMINI_API_KEY`, optional `GEMINI_MODEL` (default `gemini-3.5-flash-lite`), and optional `TIMEZONE` (default `Asia/Kolkata`) in `.env`. Obtain a key through Google AI Studio. Install with `pip install -r requirements.txt`, then run `pytest -q`.

Person 2 can import `from backend import assistant, db`, call `db.init()`, keep `assistant.new_chat()` in Streamlit session state, call `assistant.send(chat, text)`, and render `db.list_tasks()` and `db.get_blocks()`. The schedule uses declared availability only; it does not infer calendar availability. The scheduler uses whole 30-minute slots, so sub-slot effort may be rounded up, and conversational interpretation depends on Gemini and user confirmation of ambiguous details. No live Gemini request has been verified until a key is configured.
