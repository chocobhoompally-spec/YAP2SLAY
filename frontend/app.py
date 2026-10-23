"""
yap2slay — study planner UI  (Person 2)
Run from project root:  streamlit run app.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import base64
import re
from html import escape
from collections import defaultdict
from datetime import datetime, date as date_type, time as clock_time, timedelta
import time
from zoneinfo import ZoneInfo

# ensure project root on path when run via runpy
_ROOT = pathlib.Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from backend import assistant, db, scheduler_service

TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
ASSETS = pathlib.Path(__file__).parent / "assets"
ALLIE_AVATAR = ASSETS / "allie-avatar.png"
ALLIE_COMPANION = ASSETS / "allie-companion.png"
ALLIE_ARM_LEFT = ASSETS / "allie-arm-left.png"
ALLIE_ARM_RIGHT = ASSETS / "allie-arm-right.png"
USER_AVATAR = ASSETS / "user-avatar.png"
WELCOME_MESSAGE = (
    "Hi, I'm Allie — your personal study sidekick ✨ "
    "Give me your deadlines, study chaos, or the one task you keep dodging. "
    "We'll turn it into a plan and get you feeling very on top of things. "
    "What's on your plate today?"
)

def png_data_uri(path: pathlib.Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")

ALLIE_STAGE_MARKUP = f"""
<div class="allie-stage" role="img" aria-label="Allie, your pink robot study buddy">
  <div class="allie-hello" aria-hidden="true">Hii! 👋</div>
  <img class="allie-arm-left" src="{png_data_uri(ALLIE_ARM_LEFT)}" alt="">
  <img class="allie-arm-right" src="{png_data_uri(ALLIE_ARM_RIGHT)}" alt="">
  <img class="allie-body" src="{png_data_uri(ALLIE_COMPANION)}" alt="">
</div>
"""

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
::-webkit-scrollbar-thumb { background: #FFB6C1; border-radius: 0; }

/* ── top bar ── */
.topbar {
    background: #0D0D0D;
    border-bottom: 3px solid #FFB6C1;
    padding: 14px clamp(18px, 4vw, 58px);
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
    color: #FFB6C1;
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

/* ── hero / game layer ── */
.hero {
    position: relative; overflow: hidden; padding: 20px 22px 18px; margin: 0 0 18px;
    border: 1px solid #242426;
    background: radial-gradient(ellipse at 0% 0%, #321b25 0%, #171317 48%, #101011 100%);
}
.st-key-hero-panel {
    margin-bottom:18px;
}
.hero { height:100%; min-height:225px; margin:0; display:flex; flex-direction:column; justify-content:center; }
.st-key-pomodoro-panel {
    width:100%; max-width:380px; min-height:225px; margin:0 auto;
    padding:16px; border:1px solid #6d4655; border-radius:24px;
    background:radial-gradient(ellipse at 50% 25%,#633849 0%,#39242d 50%,#21181e 100%);
    box-shadow:inset 0 1px 10px #ffc5d322,0 12px 30px #0005; text-align:center;
}
.st-key-pomodoro-panel [data-testid="stVerticalBlock"] { align-items:center; }
.st-key-pomodoro-panel > div { width:100%; }
.st-key-pomodoro-panel [data-testid="stMarkdownContainer"] { text-align:center !important; }
.st-key-pomodoro-panel [data-testid="stHorizontalBlock"] { justify-content:center; }
.st-key-pomodoro-panel [data-testid="stNumberInput"] { max-width:132px; margin:0 auto 5px; }
.st-key-pomodoro-panel [data-testid="stNumberInput"] label { text-align:center !important; }
.st-key-pomodoro-panel [data-testid="stNumberInput"] input { text-align:center; color:#fff !important; background:#241b20 !important; border-color:#79505f !important; }
.st-key-pomodoro-panel [data-testid="stButton"] button { border-radius:999px !important; padding:6px 9px !important; letter-spacing:.5px !important; font-size:.55rem !important; }
.pomodoro-label { color:#ffd7e5; font:700 .56rem 'Space Mono',monospace; letter-spacing:2px; text-transform:uppercase; }
.pomodoro-time { color:#fff3f8; font:700 clamp(1.8rem,3vw,2.55rem) 'Space Grotesk',sans-serif; letter-spacing:-1px; margin:2px 0 7px; text-align:center !important; text-shadow:0 2px 15px #ffb6c155; }
.st-key-focus-toggle-active [data-testid="stButton"] button { background:#ffb6c1 !important; color:#211318 !important; box-shadow:0 0 14px #ff9fba88 !important; }
.st-key-focus-toggle-active [data-testid="stButton"] button:hover { background:#ffd2de !important; }
.pomodoro-track { height:4px; background:#51303d; border-radius:9px; overflow:hidden; margin:7px 3px 10px; }
.pomodoro-fill { height:100%; background:linear-gradient(90deg,#ff8fab,#ffe0ea); border-radius:9px; box-shadow:0 0 10px #ff8fab99; }
.hero::after {
    content: ""; position: absolute; right: 12px; top: -35px; width: 180px; height: 180px;
    border: 1px solid #ffb6c122; transform: rotate(45deg); pointer-events: none;
    box-shadow: 0 0 0 18px #ffb6c10a, 0 0 0 38px #ffb6c108;
}
.hero-kicker, .eyebrow { color: #ffb6c1; font: 700 .62rem 'Space Mono', monospace; letter-spacing: 2px; text-transform: uppercase; }
.hero-title { max-width: 700px; margin: 8px 0 4px; color: #f4f0ec; font-size: clamp(1.65rem, 3vw, 2.55rem); line-height: 1.06; font-weight: 900; letter-spacing: -1.5px; }
.hero-title em { color: #ffb6c1; font-style: normal; }
.hero-copy { color: #89868a; font: .72rem 'Space Mono', monospace; letter-spacing: .2px; }
.hero-stats { display:flex; flex-wrap:wrap; gap:8px; margin-top:15px; position:relative; z-index:1; }
.stat-pill { border:1px solid #343236; background:#111113cc; padding:6px 10px; color:#969198; font: .61rem 'Space Mono', monospace; text-transform:uppercase; letter-spacing:.5px; }
.stat-pill b { color:#ffb6c1; font-size:.72rem; }
.quick-row { display:flex; gap:7px; flex-wrap:wrap; margin: 6px 0 16px; }
.quick-row [data-testid="stButton"] button { padding: 5px 10px !important; letter-spacing:.5px !important; font-size:.58rem !important; }
.focus-card { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:9px 12px; margin:10px 0 16px; border:1px solid #49323b; background:#1c1519; color:#c5b8be; font: .64rem 'Space Mono', monospace; }
.focus-card b { color:#ffb6c1; }
.xp-track { height:5px; background:#292528; margin-top:7px; overflow:hidden; }
.xp-fill { height:100%; background:linear-gradient(90deg,#ff8fab,#ffd1dc); box-shadow:0 0 12px #ffb6c199; }

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
    font-size: 0.82rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #FFB6C1;
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
    background: #FFB6C1;
    color: #0D0D0D;
    font-weight: 600;
    border: 2px solid #FFB6C1;
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
.bubble-bot .bubble-name { color: #FFB6C1; opacity: 1; }

/* ── action chips ── */
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.chip {
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 2px 8px;
    border: 1px solid #FFB6C1;
    color: #FFB6C1;
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
    font-size: 0.76rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #aaa;
    margin: 16px 0 6px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #1E1E1E;
}
.block {
    display: flex;
    gap: 0;
    margin: 4px 0;
    background: #17171a;
    border: 1px solid #343238;
    overflow: hidden;
    transition: border-color 0.15s;
}
.block:hover { border-color: #333; }
.block-bar { width: 4px; flex-shrink: 0; }
.block-body { padding: 10px 13px; flex: 1; }
.block-title {
    font-size: 1.04rem;
    font-weight: 700;
    color: #F0EBE0;
    line-height: 1.2;
}
.block-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.76rem;
    color: #aaa;
    margin-top: 3px;
    letter-spacing: 0.5px;
}
.block-now { border-color: #FFB6C1 !important; }
.block-now .block-title::after {
    content: " ▶ NOW";
    color: #FFB6C1;
    font-size: 0.65rem;
}
.block-past { opacity: 0.68; }
.block-kind-tag {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 1px 5px;
    border: 1px solid #333;
    color: #aaa;
    margin-top: 3px;
}

/* ── task cards ── */
.task {
    background: #17171a;
    border: 1px solid #343238;
    border-left: 4px solid #333;
    padding: 10px 12px;
    margin: 5px 0;
}
.task-high   { border-left-color: #FFB6C1; }
.task-normal { border-left-color: #4A9EFF; }
.task-low    { border-left-color: #555; }
.task-title {
    font-size: 1.08rem;
    font-weight: 700;
    color: #F0EBE0;
    margin-bottom: 4px;
}
.task-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.76rem;
    color: #aaa;
    letter-spacing: 0.5px;
    line-height: 1.6;
}
.task-meta span { color: #d1bdc6; }
.progress-track {
    height: 3px;
    background: #1E1E1E;
    margin-top: 8px;
    position: relative;
}
.progress-fill {
    height: 100%;
    background: #FFB6C1;
    position: absolute;
    top: 0;
    left: 0;
}
.progress-pct {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    color: #aaa;
    margin-top: 3px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── empty state ── */
.empty {
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #aaa;
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
    padding: 8px 0;
    border-bottom: 1px solid #111;
    font-size: 0.85rem;
    flex-wrap:wrap;
}
.log-chip {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 2px 6px;
    border: 1px solid #FFB6C1;
    color: #FFB6C1;
    white-space: nowrap;
    flex-shrink: 0;
}
.log-time {
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: #999;
    white-space: nowrap;
    flex-shrink: 0;
    padding-top: 2px;
}
.log-text { color: #b2aab0; font-size: 0.84rem; line-height: 1.5; flex:1; overflow-wrap:anywhere; }
[class*="st-key-complete_task_"] button,
[class*="st-key-delete_task_"] button,
[class*="st-key-complete_block_task_"] button,
[class*="st-key-delete_block_"] button,
[class*="st-key-edit_task_popover_"] button,
[class*="st-key-edit_block_popover_"] button {
    min-height:40px; padding:7px 10px !important; font-size:.76rem !important;
    letter-spacing:1px !important; border-radius:9px !important;
}

/* ── chat input override ── */
[class*="st-key-chat-shell"] {
    position:sticky; bottom:8px; z-index:20; max-height:calc(100vh - 82px);
    background: linear-gradient(155deg, #171519, #111113 70%);
    border: 1px solid #30262c;
    border-radius: 22px;
    padding: 14px 16px 10px;
    box-shadow: 0 16px 38px #0005, inset 0 1px #ffffff08;
}
[class*="st-key-chat-history"] {
    background: #101012;
    border: 1px solid #252329;
    border-radius: 17px;
    padding: 12px 14px;
    scrollbar-color: #634550 #101012;
    scrollbar-width: thin;
    scroll-behavior:smooth;
}
[class*="st-key-chat-history"] [data-testid="stVerticalBlock"] { gap: .55rem; }
.chat-heading {
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    padding: 2px 3px 12px;
}
.chat-heading-title { color:#f7edf1; font-size:1rem; font-weight:700; }
.chat-heading-subtitle { color:#8f858b; font: .62rem 'Space Mono',monospace; margin-top:3px; }
.allie-online { color:#83e8c2; font: .58rem 'Space Mono',monospace; letter-spacing:1px; text-transform:uppercase; }
.allie-online::before { content:""; display:inline-block; width:7px;height:7px; background:#83e8c2; border-radius:50%; margin-right:7px; box-shadow:0 0 9px #83e8c277; }

/* Native Streamlit chat messages, styled as a two-sided conversation. */
[data-testid="stChatMessage"] {
    display:flex !important; width:100%; justify-content:flex-start !important;
    align-items:flex-start !important; gap:10px; margin:3px 0 9px;
    background:transparent !important; box-shadow:none !important;
}
[data-testid="stChatMessageContent"] {
    width: fit-content;
    max-width: min(78%, 680px);
    flex:0 1 auto;
    display:flex !important; flex-direction:column; justify-content:flex-start !important;
    align-items:flex-start !important; align-self:flex-start !important;
    margin:0 !important; padding:13px 17px 14px;
    background: #1b1a20;
    border: 1px solid #302d35;
    border-radius: 19px 19px 19px 6px;
    color: #f3edf0;
    overflow-wrap: anywhere;
    box-shadow: 0 4px 12px #0002;
    position:relative; overflow:visible;
}
[data-testid="stChatMessageContent"]::after {
    content:""; position:absolute; left:-7px; bottom:1px; width:12px; height:13px;
    background:#1b1a20; clip-path:polygon(100% 0,100% 100%,0 100%);
}
[data-testid="stChatMessageContent"] > div { width:100%; min-height:0 !important; flex:0 0 auto !important; align-self:stretch !important; }
[data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"] { width:100%; min-height:0 !important; }
[data-testid="stChatMessageContent"] p { margin:0 0 .55rem !important; line-height:1.5; text-align:left; }
[data-testid="stChatMessageContent"] p:last-child { margin-bottom:0; }
[data-testid="stChatMessageContent"] li { line-height:1.55; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) { flex-direction:row-reverse; }
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg,#f3b3c8,#ffc9d9);
    border-color:#ffd0df;
    border-radius:19px 19px 6px 19px;
    color:#24131b;
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"]::after {
    left:auto; right:-7px; background:#ffc9d9;
    clip-path:polygon(0 0,100% 100%,0 100%);
}
[data-testid="stChatMessageAvatarImage"] {
    width:40px !important; height:40px !important; min-width:40px !important;
    object-fit:cover !important; border-radius:50% !important;
    border:1px solid #56404a; box-shadow:0 3px 10px #0006;
}
.message-author {
    color:#ffb6c8; font:700 .58rem 'Space Mono',monospace;
    letter-spacing:1.3px; text-transform:uppercase; margin:0 0 6px;
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) .message-author { color:#684456; text-align:right; }
.allie-typing {
    position:relative; display:flex; align-items:center; justify-content:center;
    width:66px; height:42px; color:#a85d79; background:#f2b4c9;
    border:1px solid #ffd0df; border-radius:22px; box-shadow:0 4px 12px #0002;
}
.allie-typing::before,.allie-typing::after { content:""; position:absolute; background:#f2b4c9; border-radius:50%; }
.allie-typing::before { width:9px;height:9px;left:-5px;bottom:0; }
.allie-typing::after { width:5px;height:5px;left:-10px;bottom:-5px; }
.typing-dots { display:inline-flex; gap:4px; }
.typing-dots i { width:8px;height:8px;border-radius:50%;background:#ad6680;animation:typing 1s ease-in-out infinite; }
.typing-dots i:nth-child(2) { animation-delay:.15s; }
.typing-dots i:nth-child(3) { animation-delay:.3s; }
@keyframes typing { 0%,60%,100% { transform:translateY(0);opacity:.45; } 30% { transform:translateY(-4px);opacity:1; } }

[data-testid="stChatInput"] > div {
    border: 1px solid #44343d !important;
    border-radius: 999px !important;
    background: #1a181c !important;
    box-shadow: inset 0 1px 3px #0005 !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #ffb6c8 !important;
    box-shadow: 0 0 0 3px #ffb6c822 !important;
}
[data-testid="stChatInput"] textarea {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.88rem !important;
    background: transparent !important;
    color: #F0EBE0 !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInputSubmitButton"] { border-radius:50% !important; background:#f4b5c9 !important; }
[data-testid="stChatInputSubmitButton"] svg { fill: #25151d !important; }
[data-testid="stAudioInput"] { margin-top:2px; }
[data-testid="stAudioInput"] label { display:none !important; }
[data-testid="stAudioInputActionButton"] {
    width:44px !important; height:44px !important; min-width:44px !important;
    border:1px solid #70495a !important; border-radius:50% !important;
    background:#292027 !important; color:#ffc2d5 !important;
}
[data-testid="stAudioInputActionButton"]:hover { background:#f4b5c9 !important; color:#25151d !important; }
[data-testid="stAudioInput"] audio { max-width:100%; }
[data-testid="stAudioInput"] audio { display:none !important; }
.voice-equalizer {
    display:flex; align-items:center; justify-content:center; gap:3px;
    height:0; margin:0 auto; overflow:hidden; opacity:0;
    transition:height .15s ease,opacity .15s ease,margin .15s ease;
}
.voice-equalizer i {
    display:block; width:4px; height:5px; border-radius:5px;
    background:linear-gradient(180deg,#ffe2ed,#ff4e91);
    box-shadow:0 0 8px #ff4e91aa;
    animation:voiceBars .72s ease-in-out infinite alternate;
}
.voice-equalizer i:nth-child(2n) { animation-delay:-.28s; }
.voice-equalizer i:nth-child(3n) { animation-delay:-.5s; }
.voice-equalizer i:nth-child(4n) { animation-delay:-.12s; }
@keyframes voiceBars {
    from { height:5px; opacity:.65; }
    to { height:21px; opacity:1; }
}
[class*="st-key-chat-shell"]:has([data-testid="stAudioInputActionButton"][aria-label="Stop recording"]) [data-testid="stChatInput"] > div {
    border-color:#ff63a0 !important;
    box-shadow:0 0 0 3px #ff4e9133,0 0 16px #ff4e9166 !important;
}
[class*="st-key-chat-shell"]:has([data-testid="stAudioInputActionButton"][aria-label="Stop recording"]) .voice-equalizer {
    height:23px; margin:5px auto 0; opacity:1;
}
[class*="st-key-delete_voice_recording"] button,[class*="st-key-send_voice_recording"] button { width:100%; min-width:42px; height:38px; padding:0 !important; border-radius:999px !important; font-size:.95rem !important; }
.voice-ready { margin:3px 0 8px; color:#ffc0d3; font:.68rem 'Space Mono',monospace; }
.voice-action-row { display:flex; align-items:center; justify-content:flex-end; gap:10px; margin:0 0 7px; }
.voice-action-row [data-testid="stButton"] button { min-width:48px; height:40px; padding:0 !important; border-radius:999px !important; font-size:1rem !important; }
@media (prefers-reduced-motion: reduce) { .voice-equalizer i { animation:none; height:12px; } }

/* Allie lives beside the planner and reacts when hovered. */
[class*="st-key-allie-companion"] {
    position:relative; overflow:hidden; padding:14px 16px 10px;
    border:1px solid #3b2a33; border-radius:22px;
    background:radial-gradient(ellipse at 17% 20%,#39232d 0%,#1a171b 54%,#121214 100%);
    margin-bottom:18px; box-shadow:0 12px 30px #0004;
    transition:border-color .25s ease, box-shadow .25s ease, transform .25s ease;
}
[class*="st-key-allie-companion"]:hover { border-color:#ed9eb8; box-shadow:0 14px 34px #ffb6c822; transform:translateY(-2px); }
.allie-stage {
    position:relative; width:170px; height:200px; max-width:100%; margin:auto;
    animation:allieFloat 4s ease-in-out infinite;
}
.allie-stage img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; }
.allie-arm-right { transform-origin:79% 57%; }
.allie-arm-left { transform-origin:21% 57%; }
.allie-stage:hover .allie-arm-right { animation:allieArmWave .9s ease-in-out infinite; }
[class*="st-key-allie-companion-wave"] .allie-arm-right { animation:allieArmWave .9s ease-in-out 3; }
.allie-hello {
    position:absolute; z-index:2; top:10px; right:-24px; padding:7px 13px;
    border:1px solid #ffd4e1; border-radius:18px 18px 18px 5px;
    background:#f4b8cc; color:#39202b; font:700 .86rem 'Space Mono',monospace;
    white-space:nowrap; opacity:0; visibility:hidden; pointer-events:none;
    transform:translateY(5px) scale(.94); transform-origin:bottom left;
    box-shadow:0 7px 17px #0005; transition:opacity .12s ease,transform .12s ease,visibility .12s;
}
.allie-hello::after {
    content:""; position:absolute; left:9px; bottom:-6px; width:10px; height:9px;
    background:#f4b8cc; clip-path:polygon(100% 0,0 100%,100% 70%);
}
.allie-stage:hover .allie-hello,.allie-stage:focus-within .allie-hello {
    opacity:1; visibility:visible; transform:translateY(0) scale(1);
}
.allie-card-kicker { color:#f3a9c0; font:700 .58rem 'Space Mono',monospace; text-transform:uppercase; letter-spacing:2px; }
.allie-card-title { color:#fff1f6; font-size:1.32rem; font-weight:800; margin:3px 0 2px; }
.allie-card-copy { color:#d0c4ca; font-size:.95rem; line-height:1.55; }
.allie-card-prompt { color:#f2b5ca; font:700 .76rem 'Space Mono',monospace; letter-spacing:.7px; margin-top:12px; }
@keyframes allieFloat { 0%,100% { translate:0 0; } 50% { translate:0 -5px; } }
@keyframes allieArmWave {
    0%,100% { transform:rotate(0); }
    22% { transform:rotate(-138deg); }
    43% { transform:rotate(-112deg); }
    65% { transform:rotate(-140deg); }
    82% { transform:rotate(-110deg); }
}

@media (max-width: 850px) {
    .hero,.st-key-pomodoro-panel { min-height:0; }
    [class*="st-key-chat-shell"] { padding:11px; border-radius:18px; }
    [class*="st-key-chat-history"] { padding:9px; }
    [data-testid="stChatMessageContent"] { max-width:92%; padding:10px 12px; }
    [data-testid="stChatMessageAvatarImage"] { width:34px !important;height:34px !important;min-width:34px !important; }
    .allie-stage { width:145px; height:170px; }
}

/* ── reset / confirm buttons ── */
[data-testid="stButton"] button {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    border: 1px solid #FFB6C1 !important;
    background: transparent !important;
    color: #FFB6C1 !important;
    padding: 5px 14px !important;
}
[data-testid="stButton"] button:hover {
    background: #FFB6C1 !important;
    color: #0D0D0D !important;
}

/* ── spinner ── */
[data-testid="stSpinner"] { color: #FFB6C1 !important; }

/* ── warning box ── */
[data-testid="stAlert"] {
    background: #1A1500 !important;
    border: 1px solid #FFD700 !important;
    border-radius: 0 !important;
    color: #FFD700 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.7rem !important;
}

/* Make form fields readable in task and schedule popovers. */
[data-testid="stPopoverBody"] {
    background:#151317 !important; border:1px solid #59434d !important;
    border-radius:16px !important; box-shadow:0 18px 45px #000a !important;
}
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stNumberInput"] input,
[data-baseweb="select"] > div,
[data-testid="stTextArea"] textarea {
    background:#211e23 !important; color:#f5edf1 !important;
    border:1px solid #59434d !important; border-radius:9px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stDateInput"] input:focus,
[data-testid="stTimeInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color:#ffb6c1 !important; box-shadow:0 0 0 2px #ffb6c133 !important;
}
[data-testid="stPopoverBody"] label { color:#e6d8df !important; font-size:.86rem !important; }
.st-key-theme-toggle { position:fixed !important; top:10px; right:18px; z-index:1001; }
.st-key-theme-toggle [data-testid="stButton"] button {
    width:42px; height:40px; padding:0 !important; border-radius:50% !important;
    background:#1b171b !important; color:#ffd1dc !important; border:1px solid #76515e !important;
    font-size:1.15rem !important; letter-spacing:0 !important;
}
.st-key-theme-toggle [data-testid="stButton"] button:hover { background:#ffb6c1 !important; color:#24161c !important; }

/* A complete light palette, activated by the sun/moon control. */
body:has(.topbar[data-theme="light"]),
body:has(.topbar[data-theme="light"]) .stApp,
body:has(.topbar[data-theme="light"]) section[data-testid="stMain"] {
    background:#f5f1f3 !important; color:#30242b !important;
}
body:has(.topbar[data-theme="light"]) [class*="css"] { background:transparent !important; color:#30242b !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stButton"] button { color:#9a4f6b !important; border-color:#cd8da5 !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stButton"] button:hover { background:#efb4c8 !important; color:#30242b !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stPopover"] button,
body:has(.topbar[data-theme="light"]) [data-testid="stPopoverBody"] button,
body:has(.topbar[data-theme="light"]) button[kind="secondary"] {
    background:#fff8fb !important; color:#844660 !important;
    border:1px solid #d5a6b8 !important; box-shadow:none !important;
}
body:has(.topbar[data-theme="light"]) [data-testid="stPopover"] button:hover,
body:has(.topbar[data-theme="light"]) [data-testid="stPopoverBody"] button:hover,
body:has(.topbar[data-theme="light"]) button[kind="secondary"]:hover { background:#f9e6ed !important; color:#512c3b !important; }
body:has(.topbar[data-theme="light"]) .st-key-focus-toggle-active [data-testid="stButton"] button { background:#ffb6c1 !important; color:#211318 !important; }
body:has(.topbar[data-theme="light"]) .topbar { background:#fffafb; border-bottom-color:#e99db5; }
body:has(.topbar[data-theme="light"]) .topbar-tag { color:#74616a; border-color:#d8cbd1; }
body:has(.topbar[data-theme="light"]) .hero {
    background:radial-gradient(ellipse at 0 0,#fff0f5 0%,#f7edf1 52%,#eee8ec 100%);
    border-color:#dfd2d9;
}
body:has(.topbar[data-theme="light"]) .hero-title { color:#30242b; }
body:has(.topbar[data-theme="light"]) .hero-copy,
body:has(.topbar[data-theme="light"]) .chat-heading-subtitle { color:#71656b; }
body:has(.topbar[data-theme="light"]) .stat-pill { background:#fff9fb; border-color:#dccbd3; color:#71656b; }
body:has(.topbar[data-theme="light"]) [class*="st-key-chat-shell"] { background:linear-gradient(155deg,#fffafd,#f3edf1 75%); border-color:#dfd1d8; }
body:has(.topbar[data-theme="light"]) [class*="st-key-chat-history"] { background:#fffafd; border-color:#e4d9de; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatMessageContent"] { background:#fffafd; color:#30242b; border-color:#e4d6dd; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatMessageContent"]::after { background:#fffafd; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"] { background:#f3b7cb; color:#291820; border-color:#e9a7bf; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid="stChatMessageContent"]::after { background:#f3b7cb; }
body:has(.topbar[data-theme="light"]) .chat-heading-title,
body:has(.topbar[data-theme="light"]) .block-title,
body:has(.topbar[data-theme="light"]) .task-title { color:#30242b; }
body:has(.topbar[data-theme="light"]) .col-right { background:#f5f1f3; }
body:has(.topbar[data-theme="light"]) .sec-head { color:#ad5875; border-color:#dfd2d9; }
body:has(.topbar[data-theme="light"]) .day-label { color:#766a70; border-color:#e0d6db; }
body:has(.topbar[data-theme="light"]) .block,
body:has(.topbar[data-theme="light"]) .task { background:#fffafd; border-color:#e0d5db; }
body:has(.topbar[data-theme="light"]) .block-meta,
body:has(.topbar[data-theme="light"]) .task-meta,
body:has(.topbar[data-theme="light"]) .progress-pct { color:#75676e; }
body:has(.topbar[data-theme="light"]) .task-meta span { color:#8c6677; }
body:has(.topbar[data-theme="light"]) .empty { color:#81747a; border-color:#d8cbd2; }
body:has(.topbar[data-theme="light"]) .log-row { border-color:#e4dce0; }
body:has(.topbar[data-theme="light"]) .log-time,
body:has(.topbar[data-theme="light"]) .log-text { color:#71656b; }
body:has(.topbar[data-theme="light"]) [data-testid="stPopoverBody"] { background:#fffafd !important; border-color:#dacbd2 !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stTextInput"] input,
body:has(.topbar[data-theme="light"]) [data-testid="stDateInput"] input,
body:has(.topbar[data-theme="light"]) [data-testid="stTimeInput"] input,
body:has(.topbar[data-theme="light"]) [data-testid="stNumberInput"] input,
body:has(.topbar[data-theme="light"]) [data-baseweb="select"] > div,
body:has(.topbar[data-theme="light"]) [data-testid="stTextArea"] textarea { background:#fff !important; color:#30242b !important; border-color:#cdbbc4 !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stPopoverBody"] label { color:#55464e !important; }
body:has(.topbar[data-theme="light"]) .st-key-pomodoro-panel [data-testid="stNumberInput"] label { color:#55464e !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatInput"] > div { background:#fffafd !important; border-color:#d7c5ce !important; }
body:has(.topbar[data-theme="light"]) [data-testid="stChatInput"] textarea { color:#30242b !important; }
body:has(.topbar[data-theme="light"]) [class*="st-key-allie-companion"] { background:radial-gradient(ellipse at 17% 20%,#fff0f5,#f6e8ee 68%,#f2e9ed); border-color:#e1cdd6; }
body:has(.topbar[data-theme="light"]) .allie-card-title { color:#392832; }
body:has(.topbar[data-theme="light"]) .allie-card-copy { color:#64555d; }
body:has(.topbar[data-theme="light"]) .st-key-pomodoro-panel { background:radial-gradient(ellipse at 50% 25%,#fff2f7,#f2dfe7 72%,#eddde5); border-color:#d8aabc; }
body:has(.topbar[data-theme="light"]) .pomodoro-time { color:#39232c; }
body:has(.topbar[data-theme="light"]) .pomodoro-label { color:#88546a; }
body:has(.topbar[data-theme="light"]) .st-key-theme-toggle [data-testid="stButton"] button { background:#fffafd !important; color:#745161 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────
KIND_COLOR = {
    "exam":       "#FFB6C1",
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
    "delete_task":        ("⌫ removed",     "chip chip-warn"),
    "delete_schedule_block": ("⌫ schedule",  "chip chip-warn"),
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


def _configured_focus_seconds() -> int:
    return int(st.session_state.get("focus_hours", 0)) * 3600 + int(st.session_state.get("focus_minutes", 25)) * 60


def _configured_break_seconds() -> int:
    return int(st.session_state.get("break_hours", 0)) * 3600 + int(st.session_state.get("break_minutes", 5)) * 60


def close_pomodoro() -> None:
    """Hide the timer and pause it so a closed panel never runs invisibly."""
    if st.session_state.get("focus_deadline") is not None:
        st.session_state.focus_remaining = max(0, int(st.session_state.focus_deadline - time.time()))
        st.session_state.focus_deadline = None
    st.session_state.pomodoro_open = False


def _render_pomodoro_contents() -> None:
    """Render the configurable focus/break timer and its controls."""
    mode = st.session_state.pomodoro_mode
    deadline = st.session_state.focus_deadline
    if deadline is not None:
        remaining = max(0, int(deadline - time.time()))
        if remaining == 0:
            st.session_state.focus_deadline = None
            if mode == "focus":
                st.session_state.focus_cycles_completed += 1
                st.session_state.xp += 25
                completed = st.session_state.focus_cycles_completed
                if completed >= st.session_state.focus_intervals:
                    st.session_state.pomodoro_mode = "idle"
                    st.session_state.focus_remaining = _configured_focus_seconds()
                    st.toast(f"Pomodoro complete · +{completed * 25} XP ✨")
                    st.rerun()
                else:
                    break_seconds = _configured_break_seconds()
                    if break_seconds:
                        st.session_state.pomodoro_mode = "break"
                        st.session_state.focus_remaining = break_seconds
                        st.session_state.focus_deadline = time.time() + break_seconds
                        st.toast(f"Focus interval {completed} complete · break time!")
                    else:
                        st.session_state.pomodoro_mode = "focus"
                        st.session_state.focus_remaining = _configured_focus_seconds()
                        st.session_state.focus_deadline = time.time() + st.session_state.focus_remaining
            elif mode == "break":
                st.session_state.pomodoro_mode = "focus"
                st.session_state.focus_remaining = _configured_focus_seconds()
                st.session_state.focus_deadline = time.time() + st.session_state.focus_remaining
                st.toast("Break over · back to your next focus interval ✨")
            st.rerun()
        else:
            st.session_state.focus_remaining = remaining
    else:
        remaining = int(st.session_state.focus_remaining)

    with st.container(key="pomodoro-panel"):
        mode = st.session_state.pomodoro_mode
        if mode == "idle":
            focus_hours_col, focus_minutes_col = st.columns(2, gap="small")
            with focus_hours_col:
                st.session_state.focus_hours = st.number_input("Focus hours", min_value=0, max_value=12, value=int(st.session_state.focus_hours), key="focus_hours_input")
            with focus_minutes_col:
                st.session_state.focus_minutes = st.number_input("Focus minutes", min_value=0, max_value=59, value=int(st.session_state.focus_minutes), key="focus_minutes_input")
            break_hours_col, break_minutes_col = st.columns(2, gap="small")
            with break_hours_col:
                st.session_state.break_hours = st.number_input("Break hours", min_value=0, max_value=12, value=int(st.session_state.break_hours), key="break_hours_input")
            with break_minutes_col:
                st.session_state.break_minutes = st.number_input("Break minutes", min_value=0, max_value=59, value=int(st.session_state.break_minutes), key="break_minutes_input")
            st.session_state.focus_intervals = st.number_input("Focus intervals", min_value=1, max_value=20, value=int(st.session_state.focus_intervals), key="focus_intervals_input")
            focus_total = _configured_focus_seconds()
            remaining = focus_total
            st.session_state.focus_remaining = remaining
            label = "focus sprint"
            progress_total = max(1, focus_total)
        else:
            focus_total = max(1, _configured_focus_seconds())
            progress_total = max(1, _configured_break_seconds() if mode == "break" else focus_total)
            label = "break time" if mode == "break" else "focus sprint"
            completed = int(st.session_state.focus_cycles_completed)
            intervals = int(st.session_state.focus_intervals)
            st.caption(f"Interval {min(completed + (1 if mode == 'focus' else 0), intervals)} of {intervals}")

        st.markdown(f'<div class="pomodoro-label">✦ {label}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pomodoro-time">{remaining // 3600:02d}:{(remaining % 3600) // 60:02d}:{remaining % 60:02d}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pomodoro-track"><div class="pomodoro-fill" style="width:{max(0,min(100,remaining / progress_total * 100)):.1f}%"></div></div>', unsafe_allow_html=True)
        running = st.session_state.focus_deadline is not None
        start_col, reset_col, close_col = st.columns([1, 1, .55], gap="small")
        if running:
            if start_col.button("Ⅱ pause", key="pause_focus", use_container_width=True):
                st.session_state.focus_remaining = max(0, int(st.session_state.focus_deadline - time.time()))
                st.session_state.focus_deadline = None
                st.rerun()
        else:
            disabled = mode == "idle" and _configured_focus_seconds() == 0
            if start_col.button("▶ start" if mode == "idle" else "▶ resume", key="start_focus", use_container_width=True, disabled=disabled):
                if st.session_state.pomodoro_mode == "idle":
                    st.session_state.focus_cycles_completed = 0
                    st.session_state.pomodoro_mode = "focus"
                    st.session_state.focus_remaining = _configured_focus_seconds()
                st.session_state.focus_deadline = time.time() + max(1, st.session_state.focus_remaining)
                st.rerun()
        if reset_col.button("↺ reset", key="reset_focus", use_container_width=True):
            st.session_state.focus_deadline = None
            st.session_state.pomodoro_mode = "idle"
            st.session_state.focus_cycles_completed = 0
            st.session_state.focus_remaining = _configured_focus_seconds()
            st.rerun()
        if close_col.button("×", key="close_focus_panel", help="Close focus timer"):
            close_pomodoro()
            st.rerun()


_render_running_pomodoro = st.fragment(run_every=1)(_render_pomodoro_contents)


def render_pomodoro() -> None:
    """Refresh once per second only while a countdown is actively running."""
    if st.session_state.get("focus_deadline") is None:
        _render_pomodoro_contents()
    else:
        _render_running_pomodoro()


def render_chat_message(msg: dict) -> None:
    role = msg["role"]
    is_user = role == "user"
    avatar = str(USER_AVATAR if is_user else ALLIE_AVATAR)
    author = "You" if is_user else "Allie"
    with st.chat_message(role, avatar=avatar):
        st.markdown(f'<div class="message-author">{author}</div>', unsafe_allow_html=True)
        st.markdown(msg["content"])

        if not is_user:
            actions = msg.get("actions", [])
            if actions:
                chips_html = '<div class="chips">'
                for action in actions:
                    text, cls = TOOL_CHIP.get(action.get("tool", ""), (f"⚙ {action.get('tool', '')}", "chip"))
                    chips_html += f'<span class="{cls}">{text}</span>'
                chips_html += "</div>"
                st.markdown(chips_html, unsafe_allow_html=True)

            content = msg["content"].lower()
            if any(word in content for word in ("shortfall", "short by", "won't fit", "wont fit", "doesn't fit")):
                st.markdown(
                    '<div class="shortfall">⚠ schedule shortfall — some work may not fit in available time</div>',
                    unsafe_allow_html=True,
                )


_ALLIE_WAKE = re.compile(r"^\s*(?:hey|hi|hello)[,\s!—-]+all(?:ie|y)\b[,!\s?.;:—-]*", re.IGNORECASE)


def remove_wake_phrase(text: str) -> tuple[bool, str]:
    match = _ALLIE_WAKE.match(text)
    return (True, text[match.end():].strip()) if match else (False, text.strip())


# ─────────────────────────────────────────────────────────────────────────────
# session state
# ─────────────────────────────────────────────────────────────────────────────
db.init()

if "chat" not in st.session_state or isinstance(st.session_state.chat, assistant._UnavailableChat):
    st.session_state.chat = assistant.new_chat()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "allie_welcome_added" not in st.session_state:
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "assistant", "content": WELCOME_MESSAGE, "actions": []})
        st.session_state.allie_intro_wave = True
    else:
        st.session_state.allie_intro_wave = False
    st.session_state.allie_welcome_added = True
if "pending_reset" not in st.session_state: st.session_state.pending_reset = False
if "xp"            not in st.session_state: st.session_state.xp            = 0
if "focus_active"  not in st.session_state: st.session_state.focus_active  = False
if "focus_hours" not in st.session_state: st.session_state.focus_hours = 0
if "focus_minutes" not in st.session_state: st.session_state.focus_minutes = 25
if "focus_remaining" not in st.session_state: st.session_state.focus_remaining = 25 * 60
if "focus_deadline" not in st.session_state: st.session_state.focus_deadline = None
if "break_hours" not in st.session_state: st.session_state.break_hours = 0
if "break_minutes" not in st.session_state: st.session_state.break_minutes = 5
if "focus_intervals" not in st.session_state: st.session_state.focus_intervals = 4
if "focus_cycles_completed" not in st.session_state: st.session_state.focus_cycles_completed = 0
if "pomodoro_mode" not in st.session_state: st.session_state.pomodoro_mode = "idle"
if "pomodoro_open" not in st.session_state: st.session_state.pomodoro_open = False
if "theme_mode" not in st.session_state: st.session_state.theme_mode = "dark"
if "voice_input_version" not in st.session_state: st.session_state.voice_input_version = 0

# ─────────────────────────────────────────────────────────────────────────────
# top bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topbar" data-theme="{st.session_state.theme_mode}">
    <span class="topbar-logo">ϟ yap2slay</span>
    <span class="topbar-tag">with allie · student life copilot</span>
</div>
""", unsafe_allow_html=True)
if st.button("☼" if st.session_state.theme_mode == "dark" else "☾", key="theme-toggle", help="Switch between light and dark mode"):
    st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# columns
# ─────────────────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="small")

# ═════════════════════════════════════════════════════════════════════════════
# LEFT — CHAT
# ═════════════════════════════════════════════════════════════════════════════
with left:
    active_tasks = db.list_tasks(include_done=False)
    completed_tasks = [t for t in db.list_tasks(include_done=True) if t.get("status") == "done"]
    xp = st.session_state.xp + len(completed_tasks) * 50
    level = xp // 200 + 1
    level_progress = xp % 200
    hero_markup = f"""
<div class="hero">
  <div class="hero-kicker">ϟ your study sidekick · level {level}</div>
  <div class="hero-title">YAP ABOUT YOUR<br><em>PROBLEMS. SLAY THEM.</em></div>
  <div class="hero-copy">// an AI study copilot that acts, not just answers</div>
  <div class="hero-stats">
    <span class="stat-pill"><b>{len(active_tasks)}</b> active quests</span>
    <span class="stat-pill"><b>{len(completed_tasks)}</b> cleared</span>
    <span class="stat-pill"><b>{xp}</b> XP</span>
  </div>
  <div class="xp-track"><div class="xp-fill" style="width:{level_progress / 2}%"></div></div>
</div>
"""
    if st.session_state.pomodoro_open:
        with st.container(key="hero-panel"):
            hero_col, timer_col = st.columns([1.3, 1], gap="small", vertical_alignment="center")
            with hero_col:
                st.markdown(hero_markup, unsafe_allow_html=True)
            with timer_col:
                render_pomodoro()
    else:
        st.markdown(hero_markup, unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">// quick starts</div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    for col, label, prompt_text in [
        (q1, "＋ add a task", "I need to add a task"),
        (q2, "⚡ plan my day", "Help me plan my study time today"),
        (q3, "↻ life happened", "I lost an hour; replan my schedule"),
    ]:
        with col:
            if st.button(label, key=f"quick_{label}", use_container_width=True):
                st.session_state.chat_prompt = prompt_text
                st.rerun()
    with q4:
        with st.container(key="focus-toggle-active" if st.session_state.pomodoro_open else "focus-toggle-idle"):
            toggle_label = "◉ focus sprint · open" if st.session_state.pomodoro_open else "◉ start a 25 min focus sprint"
            if st.button(toggle_label, key="open_focus", use_container_width=True):
                if st.session_state.pomodoro_open:
                    close_pomodoro()
                else:
                    st.session_state.pomodoro_open = True
                st.rerun()

    with st.container(key="chat-shell"):
        st.markdown("""
<div class="chat-heading">
  <div><div class="chat-heading-title">Your chat with Allie</div>
  <div class="chat-heading-subtitle">study plans, tiny wins, deadline saves</div></div>
  <div class="allie-online">ready to help</div>
</div>
""", unsafe_allow_html=True)

        with st.container(key="chat-history", height=430, autoscroll=True):
            for msg in st.session_state.messages:
                render_chat_message(msg)
            # Keep the in-flight user message and typing bubble inside the
            # autoscrolling viewport instead of below the composer.
            pending_message = st.empty()

        # Reserve this row above the composer so recording/transcription and
        # Allie's typing indicator stay in conversational order.
        voice_actions_slot = st.empty()
        chat_input_col, mic_col = st.columns([10, 1.5], gap="small", vertical_alignment="bottom")
        with chat_input_col:
            prompt = st.chat_input("Message Allie…", key="chat_prompt")
        with mic_col:
            recording = st.audio_input(
                "Record a voice command",
                sample_rate=16000,
                key=f"voice_input_{st.session_state.voice_input_version}",
                help="Tap the mic, say your message, then stop recording.",
                label_visibility="collapsed",
            )
            voice_send = False
            voice_delete = False
            st.markdown(
                '<div class="voice-equalizer" aria-hidden="true">'
                '<i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>',
                unsafe_allow_html=True,
            )
        if recording is not None:
            with voice_actions_slot.container():
                note_col, delete_col, send_col = st.columns([8, 1, 1], gap="small", vertical_alignment="center")
                with note_col:
                    st.markdown('<div class="voice-ready">Voice note ready</div>', unsafe_allow_html=True)
                with delete_col:
                    voice_delete = st.button("🗑", key="delete_voice_recording", help="Discard voice note", use_container_width=True)
                with send_col:
                    voice_send = st.button("➤", key="send_voice_recording", help="Send voice note", use_container_width=True)

        user_text = prompt.strip() if prompt else ""
        voice_bytes = None
        voice_mime = "audio/wav"
        if voice_delete:
            st.session_state.voice_input_version += 1
            st.rerun()
        if not user_text and voice_send and recording is not None:
            voice_bytes = recording.getvalue()
            voice_mime = getattr(recording, "type", None) or "audio/wav"
            user_text = "🎙️ Voice message"
            # A sent recording cannot be submitted again after the response.
            st.session_state.voice_input_version += 1

        if user_text and voice_bytes is None:
            is_wake, command = remove_wake_phrase(user_text)
            assistant_prompt = command if is_wake else user_text
            quick_ack = is_wake and not assistant_prompt
        elif voice_bytes is not None:
            is_wake = False
            assistant_prompt = ""
            quick_ack = False
        else:
            is_wake = False
            assistant_prompt = ""
            quick_ack = voice_send

        if user_text or quick_ack:
            if user_text:
                st.session_state.messages.append({"role": "user", "content": user_text, "actions": []})
            with pending_message.container():
                if user_text:
                    render_chat_message(st.session_state.messages[-1])
                with st.chat_message("assistant", avatar=str(ALLIE_AVATAR)):
                    st.markdown('<div class="message-author">Allie</div>', unsafe_allow_html=True)
                    if not quick_ack:
                        st.markdown(
                            '<div class="allie-typing" role="status" aria-label="Allie is thinking">'
                            '<span class="typing-dots"><i></i><i></i><i></i></span></div>',
                            unsafe_allow_html=True,
                        )
                        result = assistant.send(
                            st.session_state.chat,
                            assistant_prompt,
                            audio_bytes=voice_bytes,
                            mime_type=voice_mime,
                        )
                        reply = result["reply"]
                        actions = result.get("actions", [])
                    elif user_text:
                        reply = "Yep, that's me 😌 What are we slaying today?"
                        actions = []
                    else:
                        reply = "I didn't catch that. Try again a little closer to the mic? 🎙️"
                        actions = []
                    st.markdown(reply)
                    if actions:
                        chips_html = '<div class="chips">'
                        for action in actions:
                            text, cls = TOOL_CHIP.get(action.get("tool", ""), (f"⚙ {action.get('tool', '')}", "chip"))
                            chips_html += f'<span class="{cls}">{text}</span>'
                        chips_html += "</div>"
                        st.markdown(chips_html, unsafe_allow_html=True)
                    if any(word in reply.lower() for word in ("shortfall", "short by", "won't fit", "wont fit", "doesn't fit")):
                        st.markdown(
                            '<div class="shortfall">⚠ schedule shortfall — some work may not fit in available time</div>',
                            unsafe_allow_html=True,
                        )
                    st.session_state.messages.append({"role": "assistant", "content": reply, "actions": actions})
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# RIGHT — SCHEDULE · TASKS · LOG
# ═════════════════════════════════════════════════════════════════════════════
with right:

    wave_key = "allie-companion-wave" if st.session_state.get("allie_intro_wave", False) else "allie-companion-idle"
    with st.container(key=wave_key):
        allie_image, allie_copy = st.columns([1, 1.1], vertical_alignment="center")
        with allie_image:
            st.markdown(ALLIE_STAGE_MARKUP, unsafe_allow_html=True)
        with allie_copy:
            st.markdown('<div class="allie-card-kicker">your AI study buddy</div>', unsafe_allow_html=True)
            st.markdown('<div class="allie-card-title">Allie ✨</div>', unsafe_allow_html=True)
            st.markdown('<div class="allie-card-copy">We’ll make the plan, slay the goals, and romanticize the comeback when life starts tweaking. 💅✨</div>', unsafe_allow_html=True)
            st.markdown('<div class="allie-card-prompt">HOVER TO SAY HI ↗</div>', unsafe_allow_html=True)
    st.session_state.allie_intro_wave = False

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
                st.session_state.messages      = [{"role": "assistant", "content": WELCOME_MESSAGE, "actions": []}]
                st.session_state.allie_welcome_added = True
                st.session_state.allie_intro_wave = True
                st.session_state.pending_reset = False
                st.rerun()
        with c2:
            if st.button("cancel"):
                st.session_state.pending_reset = False
                st.rerun()

    # ── SCHEDULE ─────────────────────────────────────────────────────────────
    schedule_title, schedule_add = st.columns([4, 1], vertical_alignment="center")
    with schedule_title:
        st.markdown('<p class="sec-head">// schedule</p>', unsafe_allow_html=True)
    with schedule_add:
        with st.popover("＋ add", help="Add a study block"):
            schedule_tasks = db.list_tasks(include_done=False)
            if not schedule_tasks:
                st.caption("Add a task first, then schedule it here.")
            else:
                with st.form("add_schedule_block_form"):
                    chosen_task = st.selectbox(
                        "Task", [t["id"] for t in schedule_tasks],
                        format_func=lambda task_id: next(t["title"] for t in schedule_tasks if t["id"] == task_id),
                    )
                    block_day = st.date_input("Date", value=datetime.now(TZ).date() + timedelta(days=1), key="new_block_day")
                    block_start = st.time_input("Start", value=clock_time(9, 0), key="new_block_start")
                    block_end = st.time_input("End", value=clock_time(10, 0), key="new_block_end")
                    add_block = st.form_submit_button("＋ add schedule block", use_container_width=True)
                if add_block:
                    outcome = scheduler_service.add_schedule_block(chosen_task, block_day.isoformat(), block_start.strftime("%H:%M"), block_end.strftime("%H:%M"))
                    if outcome.get("ok"):
                        st.toast("Study block added")
                        st.rerun()
                    else:
                        st.error(outcome.get("error", "Could not add that schedule block."))

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
        <div class="block-title">{escape(b['title'])}</div>
        <div class="block-meta">{fmt_t(b['start_at'])} – {fmt_t(b['end_at'])} &nbsp;·&nbsp; {mins(dur)}</div>
        <div class="block-kind-tag">{kind}</div>
    </div>
</div>""", unsafe_allow_html=True)
                done_col, edit_col, remove_col = st.columns([1, .8, .8], gap="small")
                with done_col:
                    if st.button("✓ done", key=f"complete_block_task_{b['id']}", use_container_width=True):
                        outcome = scheduler_service.complete_task(b["task_id"])
                        if outcome.get("ok"):
                            st.toast("Task complete · schedule refreshed ✨")
                        else:
                            st.error(outcome.get("error", "Could not complete that task."))
                        st.rerun()
                with edit_col:
                    with st.popover("✎ edit", key=f"edit_block_popover_{b['id']}"):
                        block_start_at = datetime.fromisoformat(b["start_at"]).astimezone(TZ)
                        block_end_at = datetime.fromisoformat(b["end_at"]).astimezone(TZ)
                        with st.form(f"edit_block_form_{b['id']}"):
                            edited_day = st.date_input("Date", value=block_start_at.date(), key=f"edit_block_day_{b['id']}")
                            edited_start = st.time_input("Start", value=block_start_at.time().replace(tzinfo=None), key=f"edit_block_start_{b['id']}")
                            edited_end = st.time_input("End", value=block_end_at.time().replace(tzinfo=None), key=f"edit_block_end_{b['id']}")
                            save_block = st.form_submit_button("Save block", use_container_width=True)
                        if save_block:
                            outcome = scheduler_service.update_schedule_block(b["id"], edited_day.isoformat(), edited_start.strftime("%H:%M"), edited_end.strftime("%H:%M"))
                            if outcome.get("ok"):
                                st.toast("Schedule block updated")
                                st.rerun()
                            else:
                                st.error(outcome.get("error", "Could not update that block."))
                with remove_col:
                    if st.button("⌫", key=f"delete_block_{b['id']}", help="Remove schedule block", use_container_width=True):
                        outcome = scheduler_service.delete_schedule_block(b["id"])
                        if outcome.get("ok"):
                            st.toast("Schedule block removed")
                        else:
                            st.error(outcome.get("error", "Could not remove that block."))
                        st.rerun()

    # ── TASKS ─────────────────────────────────────────────────────────────────
    task_title, task_add = st.columns([4, 1], vertical_alignment="center")
    with task_title:
        st.markdown('<p class="sec-head" style="margin-top:24px">// tasks</p>', unsafe_allow_html=True)
    with task_add:
        with st.popover("＋ add", help="Add a task"):
            with st.form("add_task_form"):
                new_title = st.text_input("Task")
                new_due_day = st.date_input("Due date", value=datetime.now(TZ).date() + timedelta(days=1), key="new_task_due_day")
                new_due_time = st.time_input("Due time", value=clock_time(23, 0), key="new_task_due_time")
                new_estimate = st.number_input("Estimated minutes", min_value=1, max_value=100000, value=60, step=15)
                new_kind = st.selectbox("Type", ["assignment", "exam", "reading", "personal", "other"])
                new_priority = st.selectbox("Priority", [1, 2, 3], index=1, format_func=lambda p: {1: "Low", 2: "Normal", 3: "High"}[p])
                add_task = st.form_submit_button("＋ add task", use_container_width=True)
            if add_task:
                due_value = datetime.combine(new_due_day, new_due_time, tzinfo=TZ).isoformat(timespec="minutes")
                outcome = scheduler_service.add_task(new_title, due_value, new_estimate, new_kind, new_priority)
                if outcome.get("ok"):
                    st.toast("Task added · schedule refreshed ✨")
                    st.rerun()
                else:
                    st.error(outcome.get("error", "Could not add that task."))

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
    <div class="task-title">{escape(t['title'])}</div>
    <div class="task-meta">
        <span>DUE</span> {fmt_due(t['due_at'])}<br>
        <span>LEFT</span> {mins(remaining)} &nbsp;·&nbsp; <span>PRI</span> {pri_lbl} &nbsp;·&nbsp; <span>KIND</span> {kind}
    </div>
    <div class="progress-track">
        <div class="progress-fill" style="width:{pct}%;background:{color}"></div>
    </div>
    <div class="progress-pct">{pct}% complete</div>
</div>""", unsafe_allow_html=True)
            done_col, edit_col, remove_col = st.columns([1, .8, .8], gap="small")
            with done_col:
                if st.button("✓ mark complete", key=f"complete_task_{t['id']}", use_container_width=True):
                    outcome = scheduler_service.complete_task(t["id"])
                    if outcome.get("ok"):
                        st.toast("Task complete · +50 XP ✨")
                    else:
                        st.error(outcome.get("error", "Could not complete that task."))
                    st.rerun()
            with edit_col:
                with st.popover("✎ edit", key=f"edit_task_popover_{t['id']}"):
                    due_at = datetime.fromisoformat(t["due_at"]).astimezone(TZ)
                    with st.form(f"edit_task_form_{t['id']}"):
                        edited_title = st.text_input("Task", value=t["title"], key=f"edit_task_title_{t['id']}")
                        edited_due_day = st.date_input("Due date", value=due_at.date(), key=f"edit_task_due_day_{t['id']}")
                        edited_due_time = st.time_input("Due time", value=due_at.time().replace(tzinfo=None), key=f"edit_task_due_time_{t['id']}")
                        edited_estimate = st.number_input("Estimated minutes", min_value=max(1, int(t["done_minutes"])), max_value=100000, value=int(t["est_minutes"]), step=15, key=f"edit_task_estimate_{t['id']}")
                        edited_priority = st.selectbox("Priority", [1, 2, 3], index=int(t["priority"]) - 1, format_func=lambda p: {1: "Low", 2: "Normal", 3: "High"}[p], key=f"edit_task_priority_{t['id']}")
                        save_task = st.form_submit_button("Save task", use_container_width=True)
                    if save_task:
                        new_due_value = datetime.combine(edited_due_day, edited_due_time, tzinfo=TZ)
                        old_due_value = due_at.replace(second=0, microsecond=0)
                        due_argument = new_due_value.isoformat(timespec="minutes") if new_due_value != old_due_value else ""
                        outcome = scheduler_service.update_task(t["id"], title=edited_title, due_at=due_argument, est_minutes=edited_estimate, priority=edited_priority)
                        if outcome.get("ok"):
                            st.toast("Task updated · schedule refreshed ✨")
                            st.rerun()
                        else:
                            st.error(outcome.get("error", "Could not update that task."))
            with remove_col:
                if st.button("🗑", key=f"delete_task_{t['id']}", help="Delete task", use_container_width=True):
                    outcome = scheduler_service.delete_task(t["id"])
                    if outcome.get("ok"):
                        st.toast("Task deleted and schedule refreshed")
                    else:
                        st.error(outcome.get("error", "Could not delete that task."))
                    st.rerun()

    # ── ACTION LOG ────────────────────────────────────────────────────────────
    all_actions = db.actions_since(0)
    if all_actions:
        log_title, clear_log_col = st.columns([4, 1], vertical_alignment="center")
        with log_title:
            st.markdown('<p class="sec-head" style="margin-top:24px">// log</p>', unsafe_allow_html=True)
        with clear_log_col:
            if st.button("⌫ clear", key="clear_action_log", help="Clear activity log", use_container_width=True):
                db.clear_actions()
                st.toast("Activity log cleared")
                st.rerun()
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
