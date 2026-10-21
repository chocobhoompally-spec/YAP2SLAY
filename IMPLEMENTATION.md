# Implementation Plan: AI Study Planner (Backend + AI)

> An agentic study assistant that doesn't just *suggest* a schedule. It **creates, changes, and repairs one** through real tool calls, and rebuilds the plan when life goes sideways.

**Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon
**Primary track:** Alexa+ (MCP server + simulated Alexa+ experience)
**Mini challenges:** AWS Builder (Bedrock + Strands Agents), Open Source (MIT), Friction Log bonus
**Deadline:** Oct 24, 2026, 12:30 AM IST. **Our internal deadline: Oct 23, 6 PM IST.**

---

## 1. Strategy: how we win

The rules for Alexa+ say a self-hosted **MCP server (spec 2025-11-25+, Streamable HTTP)** is the real thing, and the "simulated experience" is the beginner path. We do **both** and stack the AWS mini challenge on top:

| Layer | What it is | Why it scores |
|---|---|---|
| **MCP server** (`study-planner`) | Exposes scheduling tools over Streamable HTTP | Directly matches the Alexa+ track requirement; repo visibly imports and runs MCP |
| **Agent** (Strands Agents SDK on Amazon Bedrock) | Connects to our MCP server, turns natural language into tool calls | Qualifies for **AWS Builder**; shows "agent uses MCP tools" end to end |
| **Deterministic scheduler** (plain Python) | Does the actual time-slot math | Reliable demo. The LLM decides *what to do*, code decides *the schedule* |
| **Simulated Alexa+ web UI** (Person 2) | Chat + live calendar that updates as tools fire | The demo shows the assistant *acting*, not chatting |

**The single most important design rule:** the LLM never invents a schedule in prose. It calls tools; the tools change state; the UI renders state. If the calendar changes live while the student talks, we win the demo.

**Cut list if time runs out (in order):** voice input → persistence beyond SQLite → AWS deployment → extra tools. **Never cut:** add tasks, generate schedule, lose-time reschedule, mark complete.

---

## 2. Architecture

```
┌────────────────────┐   REST (JSON)    ┌─────────────────────────┐
│  Frontend (P2)     │ ───────────────▶ │  FastAPI  :8000         │
│  Chat + Calendar   │ ◀─────────────── │  /chat /tasks /schedule │
└────────────────────┘                  └───────────┬─────────────┘
                                                    │ Strands Agent
                                                    │ (Bedrock model)
                                                    ▼
                                        ┌─────────────────────────┐
                                        │  MCP Server :8001/mcp   │
                                        │  Streamable HTTP        │
                                        │  tools → scheduler.py   │
                                        └───────────┬─────────────┘
                                                    ▼
                                              SQLite (planner.db)
```

Why two processes: the MCP server is a standalone, spec-compliant Alexa+-style integration that any MCP client could use. The FastAPI app is just the agent host and the frontend's door. This separation is itself a talking point for judges.

---

## 3. Repo layout

```
study-planner/
├── README.md
├── IMPLEMENTATION.md
├── FRICTION_LOG.md            # keep updating from hour 1 (up to +10% bonus)
├── LICENSE                    # MIT (needed for Open Source challenge)
├── .env.example
├── requirements.txt
├── backend/
│   ├── db.py                  # SQLite setup + helpers
│   ├── models.py              # dataclasses / pydantic models
│   ├── scheduler.py           # pure-Python scheduling + rescheduling
│   ├── mcp_server.py          # FastMCP server exposing tools
│   ├── agent.py               # Strands agent + Bedrock + MCP client
│   ├── api.py                 # FastAPI app (/chat, /tasks, /schedule)
│   └── tests/
│       └── test_scheduler.py
└── frontend/                  # Person 2
```

---

## 4. Setup

### 4.1 Prerequisites
- Python 3.11+
- An AWS account with **Amazon Bedrock model access enabled** in your chosen region. **Do this first; model access approval can take time and is the most likely source of day-one blockers.** Log it in `FRICTION_LOG.md`.
- AWS credentials configured locally (`aws configure`) or via env vars.

### 4.2 Install
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install "mcp[cli]" strands-agents fastapi "uvicorn[standard]" python-dotenv pytest
pip freeze > requirements.txt
```

### 4.3 `.env.example`
```env
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=<paste a model ID you have access to in the Bedrock console>
MCP_URL=http://localhost:8001/mcp
DB_PATH=planner.db
TIMEZONE=Asia/Kolkata
```
> Check the exact model ID in your Bedrock console under model access. Pick a model with strong tool-use support.

### 4.4 Run
```bash
# terminal 1
python backend/mcp_server.py
# terminal 2
uvicorn backend.api:app --reload --port 8000
```

---

## 5. Data model (SQLite)

```sql
CREATE TABLE IF NOT EXISTS tasks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  title         TEXT NOT NULL,
  kind          TEXT DEFAULT 'assignment',   -- exam | assignment | reading | other
  due_at        TEXT NOT NULL,               -- ISO 8601 with timezone
  est_minutes   INTEGER NOT NULL,            -- total effort estimate
  done_minutes  INTEGER DEFAULT 0,
  priority      INTEGER DEFAULT 2,           -- 1 low, 2 normal, 3 high
  status        TEXT DEFAULT 'todo'          -- todo | done
);

CREATE TABLE IF NOT EXISTS availability (
  date          TEXT NOT NULL,               -- YYYY-MM-DD
  start_time    TEXT NOT NULL,               -- HH:MM
  end_time      TEXT NOT NULL                -- HH:MM
);

CREATE TABLE IF NOT EXISTS blocks (            -- the generated schedule
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id       INTEGER NOT NULL,
  start_at      TEXT NOT NULL,
  end_at        TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS actions (           -- audit log shown in the UI
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  at            TEXT NOT NULL,
  tool          TEXT NOT NULL,
  summary       TEXT NOT NULL
);
```

The `actions` table is how the frontend shows **"Added task: Physics exam → Rescheduled 6 blocks"** badges next to each chat reply. Every MCP tool writes one row. This is a cheap, high-impact demo feature.

---

## 6. The scheduler (`scheduler.py`)

Deterministic, testable, no LLM. Plans in **30-minute slots**.

### 6.1 Algorithm
1. Collect free slots from `availability`, minus any slots already in the past.
2. For each free slot in chronological order, pick the task with the highest **urgency score** among tasks that are not done, still have remaining minutes, and are due *after* the slot ends.
3. Assign the slot to that task. Merge adjacent slots for the same task into one block (cap blocks at 90 min, then force a different task or a gap).
4. After the pass, any task with remaining minutes unscheduled goes into `unscheduled` with how many minutes are missing.

### 6.2 Urgency score
```
remaining   = est_minutes - done_minutes - already_assigned_minutes
hours_left  = max((due_at - slot_start).hours, 1)
score       = priority_weight * remaining / hours_left
```
Higher score wins. Exams get a priority bump from `kind`. Work that is big *and* close wins, which is what a human tutor would do.

### 6.3 Skeleton
```python
# backend/scheduler.py
from datetime import datetime, timedelta
from dataclasses import dataclass

SLOT = timedelta(minutes=30)
MAX_BLOCK = timedelta(minutes=90)

@dataclass
class Task:
    id: int; title: str; due_at: datetime
    remaining: int          # minutes
    priority: int = 2

def urgency(t: Task, slot_start: datetime) -> float:
    hours_left = max((t.due_at - slot_start).total_seconds() / 3600, 1)
    return t.priority * t.remaining / hours_left

def build_schedule(tasks: list[Task], free_slots: list[datetime]):
    """free_slots: sorted list of 30-min slot start times."""
    remaining = {t.id: t.remaining for t in tasks}
    blocks = []                       # [(task_id, start, end)]
    last_task, run = None, timedelta(0)

    for s in free_slots:
        candidates = [
            t for t in tasks
            if remaining[t.id] > 0 and t.due_at >= s + SLOT
        ]
        if last_task and run >= MAX_BLOCK:
            candidates = [t for t in candidates if t.id != last_task] or candidates
        if not candidates:
            last_task, run = None, timedelta(0)
            continue

        pick = max(candidates, key=lambda t: urgency(
            Task(t.id, t.title, t.due_at, remaining[t.id], t.priority), s))
        remaining[pick.id] -= SLOT.seconds // 60

        if blocks and blocks[-1][0] == pick.id and blocks[-1][2] == s and run < MAX_BLOCK:
            blocks[-1] = (pick.id, blocks[-1][1], s + SLOT)
            run += SLOT
        else:
            blocks.append((pick.id, s, s + SLOT))
            run = SLOT
        last_task = pick.id

    unscheduled = {tid: m for tid, m in remaining.items() if m > 0}
    return blocks, unscheduled
```

### 6.4 Rescheduling = just rebuild
Because the scheduler is a pure function of (tasks, availability, now), every change is handled the same way:

| Student says | Tool called | Effect |
|---|---|---|
| "I lost an hour today" | `report_lost_time(60)` | Removes 60 min from today's availability, then rebuilds |
| "I finished the essay" | `complete_task(id)` | Marks done, frees time, rebuilds |
| "I only studied 30 min of physics" | `log_progress(id, 30)` | Updates `done_minutes`, rebuilds |
| "The exam moved to Thursday" | `update_task(id, due_at=...)` | Edits task, rebuilds |

Keep `done_minutes` in sync: when rebuilding, blocks in the past are treated as history and **not** deleted. Only future blocks are cleared and regenerated.

### 6.5 Be honest about impossible plans
If `unscheduled` is non-empty, the tool result must say so (`"short by 90 min on 'Physics exam'"`). The agent is instructed to tell the student plainly and suggest trade-offs. A planner that admits "this doesn't fit" is a *better* demo than one that silently overbooks.

### 6.6 Tests (write these first; they are the safety net)
```python
# backend/tests/test_scheduler.py
def test_closer_deadline_scheduled_first(): ...
def test_overbooked_reports_unscheduled(): ...
def test_lost_hour_pushes_work_and_reports_shortfall(): ...
def test_completed_task_frees_slots(): ...
def test_no_block_exceeds_90_minutes(): ...
```
Run with `pytest -q`. Five green tests means you can refactor on day 3 without fear.

---

## 7. MCP server (`mcp_server.py`)

Uses the official Python MCP SDK's `FastMCP`, served over **Streamable HTTP**.

```python
# backend/mcp_server.py
from mcp.server.fastmcp import FastMCP
from backend import db, scheduler_service as svc   # thin wrappers over scheduler.py + db.py

mcp = FastMCP("study-planner", port=8001, stateless_http=True, json_response=True)

@mcp.tool()
def add_task(title: str, due_at: str, est_minutes: int,
             kind: str = "assignment", priority: int = 2) -> dict:
    """Add a study task. due_at is ISO 8601 (e.g. 2026-10-23T09:00:00+05:30).
    kind: exam | assignment | reading | other. priority: 1 low, 2 normal, 3 high."""
    return svc.add_task(title, due_at, est_minutes, kind, priority)

@mcp.tool()
def list_tasks(include_done: bool = False) -> list[dict]:
    """List the student's tasks with remaining minutes and deadlines."""
    return svc.list_tasks(include_done)

@mcp.tool()
def set_available_time(date: str, start_time: str, end_time: str) -> dict:
    """Declare a window the student can study. date=YYYY-MM-DD, times=HH:MM (24h)."""
    return svc.set_available_time(date, start_time, end_time)

@mcp.tool()
def generate_schedule() -> dict:
    """Build the study schedule from current tasks and availability.
    Returns blocks plus any work that does not fit."""
    return svc.rebuild()

@mcp.tool()
def report_lost_time(minutes: int, date: str = "") -> dict:
    """Student lost study time (default: today). Removes it and re-plans."""
    return svc.report_lost_time(minutes, date or None)

@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task fully complete and re-plan the remaining work."""
    return svc.complete_task(task_id)

@mcp.tool()
def log_progress(task_id: int, minutes_done: int) -> dict:
    """Record study minutes completed on a task and re-plan."""
    return svc.log_progress(task_id, minutes_done)

@mcp.tool()
def update_task(task_id: int, title: str = "", due_at: str = "",
                est_minutes: int = 0, priority: int = 0) -> dict:
    """Change a task's details (empty/0 means leave unchanged) and re-plan."""
    return svc.update_task(task_id, title, due_at, est_minutes, priority)

@mcp.tool()
def get_schedule(date: str = "") -> dict:
    """Return scheduled blocks for a date (default: today and upcoming)."""
    return svc.get_schedule(date or None)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")      # serves at http://localhost:8001/mcp
```

**Rules for every tool:**
- Write one row to `actions` (`tool`, human-readable `summary`).
- Return small, structured dicts, including a `message` field the LLM can relay.
- Never raise raw exceptions; return `{"ok": false, "error": "..."}`.
- Tool docstrings are the LLM's instruction manual. Spend time on them.

**Verify it works before building anything else:**
```bash
npx @modelcontextprotocol/inspector     # connect to http://localhost:8001/mcp
```
Call `add_task` and `generate_schedule` manually. Screenshot this for the submission.

> The SDK's constructor options and module paths change between releases. If `FastMCP(...)` rejects an argument, check the installed version's docs and log it in `FRICTION_LOG.md`. That is exactly the kind of entry that earns the bonus.

---

## 8. Agent (`agent.py`)

Strands Agents SDK, Bedrock model, tools loaded **from our MCP server** so the repo visibly calls MCP.

```python
# backend/agent.py
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))

mcp_client = MCPClient(lambda: streamablehttp_client(os.environ["MCP_URL"]))
model = BedrockModel(
    model_id=os.environ["BEDROCK_MODEL_ID"],
    region_name=os.environ["AWS_REGION"],
    temperature=0.2,
)

SYSTEM_PROMPT = """You are a study-planning assistant inside a voice-style assistant experience.
You CHANGE the student's schedule by calling tools. Never describe a schedule you did not build with tools.

Rules:
1. Current date/time is provided at the start of each message. Resolve "tomorrow", "Friday", "tonight" yourself into ISO 8601 with the +05:30 offset.
2. When the student mentions deadlines or available time, call add_task / set_available_time for EACH item, then generate_schedule.
3. If they lose time, finish something, or a date changes, call the matching tool. Do not rebuild by hand.
4. If a tool reports unscheduled work, say so plainly and offer 1-2 concrete trade-offs.
5. If you must estimate effort (est_minutes), choose a sensible default, say what you assumed, and offer to adjust.
6. Ask at most ONE clarifying question, and only if you cannot proceed without it.
7. Reply in 2-4 short, warm sentences. The calendar shows the details; you give the summary.
"""

_sessions: dict[str, Agent] = {}

def open_mcp():            # call once at app startup
    mcp_client.__enter__()

def close_mcp():           # call at shutdown
    mcp_client.__exit__(None, None, None)

def get_agent(session_id: str) -> Agent:
    if session_id not in _sessions:
        tools = mcp_client.list_tools_sync()
        _sessions[session_id] = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
    return _sessions[session_id]

def chat(session_id: str, message: str) -> str:
    now = datetime.now(TZ).strftime("%A %Y-%m-%d %H:%M %Z")
    result = get_agent(session_id)(f"[Now: {now}]\n{message}")
    return str(result)
```

**Conversation memory:** one `Agent` per `session_id` keeps message history, so "move *it* to Thursday" works. Database state is the real memory; chat history is just context.

**Prompt-injection hygiene (judges notice):** task titles come from user text. Treat all tool outputs as data, not instructions. Do not let task titles alter the system behavior.

---

## 9. API (`api.py`) - the contract for Person 2

```python
# backend/api.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend import agent, db

@asynccontextmanager
async def lifespan(app):
    db.init()
    agent.open_mcp()
    yield
    agent.close_mcp()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
def chat(body: ChatIn):
    since = db.latest_action_id()
    reply = agent.chat(body.session_id, body.message)
    return {
        "reply": reply,
        "actions": db.actions_since(since),   # what the assistant actually DID
        "tasks": db.list_tasks(),
        "schedule": db.get_blocks(),
    }

@app.get("/tasks")       # for dashboard refresh
def tasks(): return db.list_tasks()

@app.get("/schedule")
def schedule(): return db.get_blocks()

@app.post("/reset")      # demo helper: wipe DB + sessions
def reset(): db.reset(); agent._sessions.clear(); return {"ok": True}
```

### Response shape (give this to Person 2 on day 1 so they can mock against it)
```json
{
  "reply": "Got it. I've added your Physics exam and Maths assignment...",
  "actions": [
    {"id": 41, "tool": "add_task", "summary": "Added task: Maths assignment (due Thu 09:00)"},
    {"id": 42, "tool": "generate_schedule", "summary": "Built 6 blocks, 0 minutes unscheduled"}
  ],
  "tasks": [
    {"id": 1, "title": "Maths assignment", "kind": "assignment",
     "due_at": "2026-10-22T09:00:00+05:30", "est_minutes": 120,
     "done_minutes": 0, "priority": 3, "status": "todo"}
  ],
  "schedule": [
    {"id": 1, "task_id": 1, "title": "Maths assignment",
     "start_at": "2026-10-21T16:00:00+05:30", "end_at": "2026-10-21T17:30:00+05:30"}
  ]
}
```

---

## 10. Build timeline

Today is **Wed Oct 21**. Submission window closes in under 3 days. Work in vertical slices: always have something that runs.

### Day 1: Wed Oct 21 (today): "Tools work"
- [ ] Create repo, add MIT `LICENSE`, `.gitignore` (include `.env`, `planner.db`)
- [ ] Enable Bedrock model access, confirm one successful Bedrock call
- [ ] `db.py` + schema + helpers
- [ ] `scheduler.py` + 5 passing tests
- [ ] `mcp_server.py` with `add_task`, `list_tasks`, `set_available_time`, `generate_schedule`
- [ ] Verify in MCP Inspector
- [ ] Send Person 2 the API contract (section 9) with mock JSON
- [ ] Start `FRICTION_LOG.md` (log *everything* annoying, as it happens)

### Day 2: Thu Oct 22: "Agent works, plan adapts"
- [ ] Remaining tools: `report_lost_time`, `complete_task`, `log_progress`, `update_task`, `get_schedule`
- [ ] `agent.py` connected to MCP + Bedrock; test through a terminal script first
- [ ] `api.py` endpoints live; Person 2 integrates (do this by **midday**, not evening)
- [ ] Run the demo script (section 12) end-to-end 3 times; fix every wobble
- [ ] Tune the system prompt and tool docstrings based on failures

### Day 3: Fri Oct 23: "Ship"
- [ ] Morning: bug fixes only, no new features
- [ ] Record demo video (under 3 min), upload to YouTube, set **public**
- [ ] README with install/run steps (a stranger must run it in 5 minutes)
- [ ] Write project description and product feedback (section 13)
- [ ] Repo: public + MIT license, **or** private with all required collaborators added (see section 14)
- [ ] **Submit by 6 PM IST.** Leave a buffer; Devpost forms and video links always take longer than expected.

---

## 11. Failure modes and mitigations

| Risk | Mitigation |
|---|---|
| Bedrock access or quota blocks us | Request access today; keep a second model option in `.env`; log it |
| LLM picks wrong date or timezone | "Now" injected every turn; tool validates ISO strings and rejects past due dates with a clear error |
| Agent forgets to call `generate_schedule` | Make state-changing tools (`complete_task`, `report_lost_time`, etc.) rebuild internally, so correctness never depends on the LLM remembering |
| Demo flakiness | Seed script plus `/reset`; rehearse with the exact demo prompts; pre-record a backup take |
| MCP client session drops | Open once at startup; wrap `chat()` in a retry that re-enters the client |
| Plan can't fit in available time | This is a *feature*: surface `unscheduled` and show the agent negotiating trade-offs |
| Teammates' halves don't connect | Contract-first (section 9). Integrate on Day 2 midday, not Day 3 |

---

## 12. Demo script (under 3 minutes; lead with the best part)

**0:00 - 0:15, Hook.** "Study planners tell you what to do. Ours does it, and fixes it when your day falls apart."

**0:15 - 1:00, Scene 1: Plan creation.**
Type or say: *"I have an exam on Friday, an assignment due tomorrow morning, and only four hours to study today."*
→ Show tool-action badges firing (`add_task` ×2, `set_available_time`, `generate_schedule`) and the calendar filling in live.

**1:00 - 1:45, Scene 2: Life happens.**
*"I just lost an hour."*
→ Calendar visibly reshuffles; assignment stays protected, exam prep spreads into tomorrow. Agent explains the trade-off in one sentence.

**1:45 - 2:15, Scene 3: Progress and honesty.**
*"I finished the assignment."* → Marked complete, schedule re-optimizes.
*"Add a chemistry quiz on Thursday."* → Agent warns that it only partly fits and offers options.

**2:15 - 2:45, Under the hood.**
One quick architecture shot: MCP server (Streamable HTTP) → Strands agent on Bedrock → SQLite. Show the MCP Inspector for 3 seconds. "Any Alexa+-compatible MCP client can plug into this."

**2:45 - 3:00, Close.** What it is, who it helps, repo URL.

> Do **not** use copyrighted music or third-party logos in the video. Narrate over it.

---

## 13. Submission checklist

**Devpost fields**
- [ ] Project description: what it does and how it works
- [ ] Primary track: **Alexa+** (state both: real MCP server + simulated Alexa+ web experience)
- [ ] Mini challenges: **AWS Builder**, **Open Source**
- [ ] Demo video link (YouTube/Vimeo, public, English, < 3 min)
- [ ] GitHub repo link
- [ ] Product feedback for **every** tool used: MCP SDK, Strands Agents, Bedrock, FastAPI, MCP Inspector (what you used it for, what worked, what needs work, onboarding feel, would you build with it again)
- [ ] **AWS Builder details:** name the services (Amazon Bedrock model invocation, Strands Agents SDK) and describe how they're used (agent loop, tool calling against our MCP server)
- [ ] **Open Source extras:** repo URL, your GitHub username, short description of what/how/why
- [ ] Friction log entries (task attempted, steps, expected vs actual, severity, workaround, suggestion)
- [ ] Optional: feature requests (with urgency: critical / important / nice-to-have)
- [ ] "Existed before the hackathon?" Answer honestly (if new, say so)

**Repo requirements**
- [ ] All source, assets, and run instructions included
- [ ] Code visibly **imports and runs MCP** (`mcp_server.py`, `agent.py`)
- [ ] Simulation source code included (frontend + backend)
- [ ] No secrets committed (`.env` ignored; rotate any key that leaked)
- [ ] `LICENSE` file present (MIT)

---

## 14. Repo visibility: pick one

**Option A (recommended): public + MIT.** Satisfies the repo requirement and the Open Source challenge in one move. Keep secrets out of history.

**Option B: private.** Share with `testing@devpost.com` plus the Amazon team *at submission time*: `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar` (Repo → Settings → Collaborators → Add people). Each must accept; invitations expire after 7 days, so add them on Oct 23, not earlier.

Note: Option B alone does not satisfy the Open Source challenge, which needs an open-source license on the project or a public contribution.

---

## 15. Friction log template (`FRICTION_LOG.md`)

Up to a 10% judging bonus. Log as you go; reconstructing later produces vague entries.

```markdown
### [Tool/SDK name]: short title
- **Task attempted:**
- **Steps taken:**
- **Expected:**
- **Actual:**
- **Severity:** blocker | major | minor | cosmetic
- **Workaround:**
- **Suggestion:**
```

Likely sources of real entries: Bedrock model access approval, Strands + MCP client lifecycle, FastMCP constructor/transport options, Streamable HTTP session handling, timezone and date resolution in agent prompts.

---

## 16. Definition of done

- [ ] One natural-language message creates multiple tasks and a full schedule via tool calls
- [ ] "I lost an hour" visibly rearranges future blocks and reports any shortfall
- [ ] Completing a task frees time and replans
- [ ] UI shows what the assistant *did* (action badges), not just what it *said*
- [ ] Fresh clone runs from the README in under 10 minutes
- [ ] Demo video under 3 minutes, public, uploaded
- [ ] Submitted before the internal deadline

> Priority order when in doubt: **working demo > clean repo > extra features.** Don't trade the first for the rest.
