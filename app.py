# Entry point — all UI code lives in frontend/app.py
# Run with: streamlit run app.py
import sys, pathlib, os

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── inject Streamlit Cloud secrets into os.environ ────────────────────────
# On Streamlit Cloud, secrets live in st.secrets, not os.environ.
# We copy them over so the backend (which uses os.getenv) can find them.
try:
    import streamlit as st
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass  # not running on Streamlit Cloud, or no secrets defined

# ── load local .env for local dev (does not override cloud secrets) ────────
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

# ── run the frontend ───────────────────────────────────────────────────────
exec(
    compile(
        open(ROOT / "frontend" / "app.py").read(),
        str(ROOT / "frontend" / "app.py"),
        "exec",
    ),
    {"__file__": str(ROOT / "frontend" / "app.py"), "__name__": "__main__"},
)
