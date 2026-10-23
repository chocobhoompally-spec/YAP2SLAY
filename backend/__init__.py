# Backend package.
# Environment variables (GEMINI_API_KEY, TIMEZONE, DB_PATH) are loaded
# by the entry point (app.py) before any backend module is imported.
# Do NOT call load_dotenv() here — it runs too late on Streamlit Cloud
# and can silently overwrite values that were already set from st.secrets.
