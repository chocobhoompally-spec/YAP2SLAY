"""
yap2slay — study planner UI  (Person 2)
Run from project root:  streamlit run app.py
"""
from __future__ import annotations

import os
import pathlib
import sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

# ensure project root on path when run via runpy
_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from backend import assistant, db

TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))

# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="yap2slay",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;900&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');

/* ── reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    font-family: 'Space Grotesk', sans-serif !important;
    background: #0D0D0D !important;
    color: #F0EBE0 !important;
}

/* hide streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stMain"] > div { padding: 0 !important; }

/* ── scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0D0D0D; }
::-webkit-scrollbar-thumb { background: #FF4500; border-radius: 0; }

/* ── top bar ── */
.topbar {
    background: #0D0D0D;
    border-bottom: 3px solid #FF4500;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 999;
}
.topbar-logo {
    font-family: 'Space Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #FF4500;
    letter-spacing: -1px;
    text-transform: uppercase;
}
.topbar-tag {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    color: #555;
    letter-spacing: 3px;
    text-transform: uppercase;
    border: 1px solid #333;
    padding: 3px 8px;
}

/* ── two-column layout ── */
.layout {
    display: grid;
    grid-template-columns: 1fr 420px;
    height: calc(100vh - 55px);
    overflow: hidden;
}
.col-chat {
    border-right: 2px solid #1E1E1E;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}
.col-right {
    overflow-y: auto;
    padding: 20px 16px;
    background: #0D0D0D;
}

/* ── section heading ── */
.sec-head {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #FF4500;
    border-bottom: 1px solid #1E1E1E;
    padding-bottom: 6px;
    margin-bottom: 10px;
}

/* ── messages area ── */
.messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px 20px 8px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

/* ── chat bubbles ── */
.bubble-wrap-user { display: flex; justify-content: flex-end; }
.bubble-wrap-bot  { display: flex; justify-content: flex-start; }

.bubble {
    max-width: 78%;
    padding: 12px 16px;
    font-size: 0.9rem;
    line-height: 1.55;
    word-break: break-word;
    position: relative;
}
.bubble-user {
    background: #FF4500;
    color: #0D0D0D;
    font-weight: 600;
    border: 2px solid #FF4500;
    clip-path: polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%);
}
.bubble-bot {
    background: #141414;
    color: #F0EBE0;
    border: 2px solid #1E1E1E;
    clip-path: polygon(0 0, 100% 0, 100% 100%, 10px 100%, 0 calc(100% - 10px));
}
.bubble-name {
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 5px;
    opacity: 0.6;
}
.bubble-bot .bubble-name { color: #FF4500; opacity: 1; }

/* ── action chips ── */
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.chip {
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 2px 8px;
    border: 1px solid #FF4500;
    color: #FF4500;
    background: transparent;
}
.chip-done  { border-color: #00C896; color: #00C896; }
.chip-warn  { border-color: #FFD700; color: #FFD700; }
.chip-info  { border-color: #4A9EFF; color: #4A9EFF; }

/* ── shortfall banner ── */
.shortfall {
    background: #1A1500;
    border: 2px solid #FFD700;
    padding: 8px 12px;
    margin-top: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #FFD700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── schedule blocks ── */
.day-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #555;
    margin: 16px 0 6px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #1E1E1E;
}
.block {
    display: flex;
    gap: 0;
    margin: 4px 0;
    background: #141414;
    border: 1px solid #1E1E1E;
    overflow: hidden;
    transition: border-color 0.15s;
}
.block:hover { border-color: #333; }
.block-bar { width: 4px; flex-shrink: 0; }
.block-body { padding: 8px 12px; flex: 1; }
.block-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #F0EBE0;
    line-height: 1.2;
}
.block-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem;
    color: #555;
    margin-top: 3px;
    letter-spacing: 0.5px;
}
.block-now { border-color: #FF4500 !important; }
.block-now .block-title::after {
    content: " ▶ NOW";
    color: #FF4500;
    font-size: 0.65rem;
}
.block-past { opacity: 0.35; }
.block-kind-tag {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 1px 5px;
    border: 1px solid #333;
    color: #555;
    margin-top: 3px;
}

/* ── task cards ── */
.task {
    background: #141414;
    border: 1px solid #1E1E1E;
    border-left: 4px solid #333;
    padding: 10px 12px;
    margin: 5px 0;
}
.task-high   { border-left-color: #FF4500; }
.task-normal { border-left-color: #4A9EFF; }
.task-low    { border-left-color: #555; }
.task-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #F0EBE0;
    margin-bottom: 4px;
}
.task-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem;
    color: #555;
    letter-spacing: 0.5px;
    line-height: 1.6;
}
.task-meta span { color: #888; }
.progress-track {
    height: 3px;
    background: #1E1E1E;
    margin-top: 8px;
    position: relative;
}
.progress-fill {
    height: 100%;
    background: #FF4500;
    position: absolute;
    top: 0;
    left: 0;
}
.progress-pct {
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem;
    color: #555;
    margin-top: 3px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── empty state ── */
.empty {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: #333;
    text-align: center;
    padding: 28px 16px;
    letter-spacing: 2px;
    text-transform: uppercase;
    border: 1px dashed #1E1E1E;
    margin: 8px 0;
    line-height: 2;
}

/* ── action log ── */
.log-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 5px 0;
    border-bottom: 1px solid #111;
    font-size: 0.75rem;
}
.log-chip {
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid #FF4500;
    color: #FF4500;
    white-space: nowrap;
    flex-shrink: 0;
}
.log-time {
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem;
    color: #333;
    white-space: nowrap;
    flex-shrink: 0;
    padding-top: 2px;
}
.log-text { color: #666; font-size: 0.72rem; line-height: 1.4; }

/* ── chat input override ── */
[data-testid="stChatInput"] > div {
    border: 2px solid #1E1E1E !important;
    border-radius: 0 !important;
    background: #141414 !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #FF4500 !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.88rem !important;
    background: transparent !important;
    color: #F0EBE0 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: #FF4500 !important; }

/* ── reset / confirm buttons ── */
[data-testid="stButton"] button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    border: 1px solid #FF4500 !important;
    background: transparent !important;
    color: #FF4500 !important;
    padding: 5px 14px !important;
}
[data-testid="stButton"] button:hover {
    background: #FF4500 !important;
    color: #0D0D0D !important;
}

/* ── spinner ── */
[data-testid="stSpinner"] { color: #FF4500 !important; }

/* ── warning box ── */
[data-testid="stAlert"] {
    background: #1A1500 !important;
    border: 1px solid #FFD700 !important;
    border-radius: 0 !important;
    color: #FFD700 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.7rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────
KIND_COLOR = {
    "exam":       "#FF4500",
    "assignment": "#4A9EFF",
    "reading":    "#00C896",
    "personal":   "#A78BFA",
    "other":      "#555555",
}
PRI_CLASS = {1: "task-low", 2: "task-normal", 3: "task-high"}
PRI_LABEL = {1: "LOW", 2: "MED", 3: "HIGH"}
TOOL_CHIP = {
    "add_task":           ("✚ added",      "chip"),
    "complete_task":      ("✔ done",        "chip chip-done"),
    "generate_schedule":  ("⚡ replanned",  "chip"),
    "set_available_time": ("⏱ avail",       "chip chip-info"),
    "report_lost_time":   ("⚠ lost time",  "chip chip-warn"),
    "block_time":         ("⛔ blocked",    "chip chip-warn"),
    "log_progress":       ("▶ progress",   "chip chip-info"),
    "update_task":        ("✎ updated",    "chip"),
    "list_tasks":         ("≡ listed",     "chip chip-info"),
}


def fmt_t(iso: str) -> str:
    try: return datetime.fromisoformat(iso).astimezone(TZ).strftime("%H:%M")
    except Exception: return iso[:5]

def fmt_day(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso).astimezone(TZ)
        return d.strftime("%A, %d %b").upper()
    except Exception: return iso[:10]

def fmt_due(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso).astimezone(TZ)
        return d.strftime("%d %b · %H:%M")
    except Exception: return iso[:16]

def mins(m: int) -> str:
    if m < 60: return f"{m}m"
    h, r = divmod(m, 60)
    return f"{h}h {r}m" if r else f"{h}h"


# ─────────────────────────────────────────────────────────────────────────────
# session state
# ─────────────────────────────────────────────────────────────────────────────
db.init()

if "chat"          not in st.session_state: st.session_state.chat          = assistant.new_chat()
if "messages"      not in st.session_state: st.session_state.messages      = []
if "pending_reset" not in st.session_state: st.session_state.pending_reset = False

# ─────────────────────────────────────────────────────────────────────────────
# top bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <span class="topbar-logo">⚡ yap2slay</span>
    <span class="topbar-tag">student life copilot</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# columns
# ─────────────────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="small")

# ═════════════════════════════════════════════════════════════════════════════
# LEFT — CHAT
# ═════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown('<p class="sec-head">// chat</p>', unsafe_allow_html=True)

    # --- render messages using native st.chat_message for proper layout ---
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("**Hey!** Tell me what's on your plate — exams, assignments, deadlines — and how much time you have. I'll build your schedule and fix it when life happens. 🗓️")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant":
                actions = msg.get("actions", [])
                if actions:
                    chips_html = '<div class="chips">'
                    for a in actions:
                        text, cls = TOOL_CHIP.get(a.get("tool",""), (f"⚙ {a.get('tool','')}", "chip"))
                        chips_html += f'<span class="{cls}">{text}</span>'
                    chips_html += "</div>"
                    st.markdown(chips_html, unsafe_allow_html=True)

                content = msg["content"].lower()
                if any(w in content for w in ("shortfall","short by","won't fit","wont fit","doesn't fit")):
                    st.markdown(
                        '<div class="shortfall">⚠ schedule shortfall — some work may not fit in available time</div>',
                        unsafe_allow_html=True
                    )

    # --- chat input ---
    prompt = st.chat_input("What's on your plate today?")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt, "actions": []})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("thinking…"):
                result = assistant.send(st.session_state.chat, prompt)

            reply   = result["reply"]
            actions = result.get("actions", [])

            st.markdown(reply)

            if actions:
                chips_html = '<div class="chips">'
                for a in actions:
                    text, cls = TOOL_CHIP.get(a.get("tool",""), (f"⚙ {a.get('tool','')}", "chip"))
                    chips_html += f'<span class="{cls}">{text}</span>'
                chips_html += "</div>"
                st.markdown(chips_html, unsafe_allow_html=True)

            if any(w in reply.lower() for w in ("shortfall","short by","won't fit","wont fit","doesn't fit")):
                st.markdown(
                    '<div class="shortfall">⚠ schedule shortfall — some work may not fit in available time</div>',
                    unsafe_allow_html=True
                )

            st.session_state.messages.append({"role": "assistant", "content": reply, "actions": actions})

        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# RIGHT — SCHEDULE · TASKS · LOG
# ═════════════════════════════════════════════════════════════════════════════
with right:

    # reset button
    if st.button("↺ reset demo"):
        st.session_state.pending_reset = True

    if st.session_state.pending_reset:
        st.warning("⚠ This will wipe everything. Sure?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("yes, wipe it"):
                db.reset()
                st.session_state.chat          = assistant.new_chat()
                st.session_state.messages      = []
                st.session_state.pending_reset = False
                st.rerun()
        with c2:
            if st.button("cancel"):
                st.session_state.pending_reset = False
                st.rerun()

    # ── SCHEDULE ─────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head">// schedule</p>', unsafe_allow_html=True)

    blocks  = db.get_blocks()
    now_iso = datetime.now(TZ).isoformat()

    if not blocks:
        st.markdown('<div class="empty">no blocks yet<br>tell me your deadlines + free time</div>', unsafe_allow_html=True)
    else:
        by_day: dict[str, list] = defaultdict(list)
        for b in blocks:
            by_day[b["start_at"][:10]].append(b)

        for day_key in sorted(by_day.keys()):
            st.markdown(f'<div class="day-label">{fmt_day(day_key + "T00:00:00")}</div>', unsafe_allow_html=True)
            for b in by_day[day_key]:
                is_past    = b["end_at"]    < now_iso
                is_current = b["start_at"] <= now_iso < b["end_at"]
                extra_cls  = "block-past" if is_past else ("block-now" if is_current else "")

                task_row = db.get_task(b["task_id"])
                kind     = task_row["kind"] if task_row else "other"
                color    = KIND_COLOR.get(kind, "#555")
                dur      = int((datetime.fromisoformat(b["end_at"]) - datetime.fromisoformat(b["start_at"])).total_seconds() / 60)

                st.markdown(f"""
<div class="block {extra_cls}">
    <div class="block-bar" style="background:{color}"></div>
    <div class="block-body">
        <div class="block-title">{b['title']}</div>
        <div class="block-meta">{fmt_t(b['start_at'])} – {fmt_t(b['end_at'])} &nbsp;·&nbsp; {mins(dur)}</div>
        <div class="block-kind-tag">{kind}</div>
    </div>
</div>""", unsafe_allow_html=True)

    # ── TASKS ─────────────────────────────────────────────────────────────────
    st.markdown('<p class="sec-head" style="margin-top:24px">// tasks</p>', unsafe_allow_html=True)

    tasks = db.list_tasks(include_done=False)

    if not tasks:
        st.markdown('<div class="empty">no active tasks<br>add one in chat</div>', unsafe_allow_html=True)
    else:
        for t in tasks:
            pct       = int(t["done_minutes"] / t["est_minutes"] * 100) if t["est_minutes"] else 0
            pri_cls   = PRI_CLASS.get(t["priority"], "task-normal")
            pri_lbl   = PRI_LABEL.get(t["priority"], "MED")
            kind      = t.get("kind", "other")
            color     = KIND_COLOR.get(kind, "#555")
            remaining = t["est_minutes"] - t["done_minutes"]

            st.markdown(f"""
<div class="task {pri_cls}">
    <div class="task-title">{t['title']}</div>
    <div class="task-meta">
        <span>DUE</span> {fmt_due(t['due_at'])}<br>
        <span>LEFT</span> {mins(remaining)} &nbsp;·&nbsp; <span>PRI</span> {pri_lbl} &nbsp;·&nbsp; <span>KIND</span> {kind}
    </div>
    <div class="progress-track">
        <div class="progress-fill" style="width:{pct}%;background:{color}"></div>
    </div>
    <div class="progress-pct">{pct}% complete</div>
</div>""", unsafe_allow_html=True)

    # ── ACTION LOG ────────────────────────────────────────────────────────────
    all_actions = db.actions_since(0)
    if all_actions:
        st.markdown('<p class="sec-head" style="margin-top:24px">// log</p>', unsafe_allow_html=True)
        for a in reversed(all_actions[-10:]):
            text, cls = TOOL_CHIP.get(a.get("tool",""), (f"⚙ {a.get('tool','')}", "chip"))
            try:    at_s = datetime.fromisoformat(a["at"]).astimezone(TZ).strftime("%H:%M")
            except: at_s = "—"
            st.markdown(f"""
<div class="log-row">
    <span class="log-chip">{text}</span>
    <span class="log-time">{at_s}</span>
    <span class="log-text">{a['summary']}</span>
</div>""", unsafe_allow_html=True)
