# Entry point — all UI code lives in frontend/app.py
# Run with: streamlit run app.py
import sys, pathlib, os

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Load .env for local dev. On Streamlit Cloud secrets are already in os.environ
# so we do NOT override — cloud values take precedence.
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)

# Execute frontend/app.py in this scope so Streamlit sees
# set_page_config and all widgets at the top level
exec(
    compile(
        open(ROOT / "frontend" / "app.py").read(),
        str(ROOT / "frontend" / "app.py"),   # correct __file__ for the exec
        "exec",
    ),
    {"__file__": str(ROOT / "frontend" / "app.py"), "__name__": "__main__"},
)
