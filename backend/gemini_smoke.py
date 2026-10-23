"""Explicit live Gemini connectivity check; run with `python backend/gemini_smoke.py`."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    # Use the project's root .env without relying on python-dotenv's stack walk.
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=project_root / ".env")

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
    if not api_key:
        print("Gemini smoke test not run: GEMINI_API_KEY is missing. Set it in the project .env file.")
        return 2
    if not model:
        print("Gemini smoke test not run: GEMINI_MODEL is empty. Set a supported model in .env.")
        return 2

    try:
        from google import genai

        client = genai.Client(api_key=api_key, vertexai=False)
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: yap2slay connection successful",
        )
        if not (getattr(response, "text", None) or "").strip():
            print(f"Gemini request reached model '{model}', but it returned no text. Check model/API configuration.")
            return 1
        print(f"Gemini live request succeeded using configured model '{model}'.")
        return 0
    except Exception as exc:
        # Do not print exception text: some SDK/network errors can include request details.
        error_type = type(exc).__name__
        code = getattr(exc, "code", None)
        if code in (401, 403):
            message = "Gemini rejected the API key. Check that GEMINI_API_KEY is valid and enabled."
        elif code == 404:
            message = f"Gemini model '{model}' was not found or is unavailable. Check GEMINI_MODEL."
        elif code == 429:
            message = "Gemini rate limit or quota reached. Check API quota and try again later."
        elif code is not None:
            message = f"Gemini API request failed (HTTP {code}). Check API settings and try again."
        elif error_type in {"TimeoutError", "ConnectError", "ConnectionError", "NetworkError"}:
            message = "Could not reach Gemini due to a network problem. Check your connection and try again."
        else:
            message = f"Gemini smoke test failed ({error_type}). Check the model, API key, network, and quota."
        print(message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
