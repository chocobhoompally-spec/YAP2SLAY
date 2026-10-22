# yap2slay

An Alexa+-style study planner demo for the Build, Ship, Shape hackathon. Python tools update SQLite, a deterministic scheduler rebuilds the plan, and Gemini interprets chat requests when configured. This is a simulated web experience; it is not an official Alexa service and does not connect to an Alexa+ device.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Create a Gemini API key in Google AI Studio and add it to `.env` as `GEMINI_API_KEY`. The defaults are `GEMINI_MODEL=gemini-3.5-flash`, `TIMEZONE=Asia/Kolkata`, and `DB_PATH=planner.db`. Never commit `.env` or the local database.

Run the tests with `pytest -q`. The frontend belongs to Person 2 and is not in this checkout. Once `app.py` is integrated, start it with `streamlit run app.py`.

## Frontend contract

```python
from backend import assistant, db

db.init()
chat = assistant.new_chat()  # keep in Streamlit session state
result = assistant.send(chat, "...")  # {"reply": str, "actions": [{tool, summary, at, id}]}
tasks = db.list_tasks()
blocks = db.get_blocks()  # id, task_id, title, start_at, end_at
```

For details on persistence, replanning, modules, and current limitations, see [backend/README.md](backend/README.md) and [IMPLEMENTATION.md](IMPLEMENTATION.md).
