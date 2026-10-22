# Entry point: streamlit run app.py
# Runs frontend/app.py as a script in this process so Streamlit
# sees set_page_config and all widgets at the top level.
import sys, pathlib, os, runpy

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Inject Streamlit Cloud secrets into os.environ BEFORE frontend runs
try:
    import streamlit as st
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass

# Load local .env for local dev (won't override cloud secrets set above)
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except Exception:
    pass

runpy.run_path(
    str(ROOT / "frontend" / "app.py"),
    init_globals={"__file__": str(ROOT / "frontend" / "app.py")},
    run_name="__main__",
)
