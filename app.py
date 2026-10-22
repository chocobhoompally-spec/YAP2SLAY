# Entry point — delegates everything to frontend/app.py
# Run with: streamlit run app.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from frontend.app import *  # noqa: F401,F403
