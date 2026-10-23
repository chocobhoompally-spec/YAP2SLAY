# Entry point: streamlit run app.py
# All UI code lives in frontend/app.py.
import sys, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── 1. inject Streamlit Cloud secrets into os.environ ─────────────────────
# Must happen before any backend module is imported anywhere.
try:
    import streamlit as st
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass  # local dev — st.secrets not available at this point

# ── 2. load local .env for local dev ──────────────────────────────────────
# override=False means cloud secrets already in os.environ are never clobbered.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except Exception:
    pass

# ── 3. run frontend/app.py in THIS module's globals ───────────────────────
# Using exec (not runpy) so Streamlit sees set_page_config at the top level
# and all backend modules share the same import state as this process.
_src  = (ROOT / "frontend" / "app.py").read_text(encoding="utf-8")
_code = compile(_src, str(ROOT / "frontend" / "app.py"), "exec")
exec(_code, {**globals(), "__file__": str(ROOT / "frontend" / "app.py")})
