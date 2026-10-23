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
  <div class="allie-hello" aria-hidden="true">Hi! 👋</div>
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
    font-size: 0.6rem;
    letter-spacing: 4px;
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
.block-now { border-color: #FFB6C1 !important; }
.block-now .block-title::after {
    content: " ▶ NOW";
    color: #FFB6C1;
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
.task-high   { border-left-color: #FFB6C1; }
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
    background: #FFB6C1;
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
    border: 1px solid #FFB6C1;
    color: #FFB6C1;
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
[class*="st-key-chat-shell"] {
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
if "voice_input_version" not in st.session_state: st.session_state.voice_input_version = 0

# ─────────────────────────────────────────────────────────────────────────────
# top bar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <span class="topbar-logo">ϟ yap2slay</span>
    <span class="topbar-tag">with allie · student life copilot</span>
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
    active_tasks = db.list_tasks(include_done=False)
    completed_tasks = [t for t in db.list_tasks(include_done=True) if t.get("status") == "done"]
    xp = st.session_state.xp + len(completed_tasks) * 50
    level = xp // 200 + 1
    level_progress = xp % 200
    st.markdown(f"""
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
""", unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">// quick starts</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    for col, label, prompt_text in [
        (q1, "＋ add a task", "I need to add a task"),
        (q2, "⚡ plan my day", "Help me plan my study time today"),
        (q3, "↻ life happened", "I lost an hour; replan my schedule"),
    ]:
        with col:
            if st.button(label, key=f"quick_{label}", use_container_width=True):
                st.session_state.chat_prompt = prompt_text
                st.rerun()

    if st.session_state.focus_active:
        st.markdown('<div class="focus-card"><span>◉ <b>FOCUS MODE</b> · protect your next 25 minutes</span></div>', unsafe_allow_html=True)
        if st.button("✓ finish focus · claim 25 XP", key="finish_focus"):
            st.session_state.xp += 25
            st.session_state.focus_active = False
            st.rerun()
    elif st.button("◉ start a 25 min focus sprint", key="start_focus"):
        st.session_state.focus_active = True
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

        pending_message = st.empty()
        chat_input_col, mic_col = st.columns([8, 1], gap="small", vertical_alignment="bottom")
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
            st.markdown(
                '<div class="voice-equalizer" aria-hidden="true">'
                '<i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>',
                unsafe_allow_html=True,
            )

        user_text = prompt.strip() if prompt else ""
        if not user_text and recording is not None:
            # Rotate the widget key so the completed recording cannot be
            # submitted again on the next Streamlit rerun.
            st.session_state.voice_input_version += 1
            listening = st.empty()
            with listening.container():
                with st.chat_message("assistant", avatar=str(ALLIE_AVATAR)):
                    st.markdown('<div class="message-author">Allie</div>', unsafe_allow_html=True)
                    with st.spinner("Listening to your voice message…"):
                        user_text = assistant.transcribe_audio(
                            st.session_state.chat,
                            recording.getvalue(),
                            getattr(recording, "type", None) or "audio/wav",
                        )
            listening.empty()

        if user_text:
            is_wake, command = remove_wake_phrase(user_text)
            assistant_prompt = command if is_wake else user_text
            quick_ack = is_wake and not assistant_prompt
        else:
            is_wake = False
            assistant_prompt = ""
            quick_ack = recording is not None

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
                        with st.spinner("Allie is thinking…"):
                            result = assistant.send(st.session_state.chat, assistant_prompt)
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
