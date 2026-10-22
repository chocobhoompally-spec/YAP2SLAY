# Friction Log

### Python package installation: sandbox could not reach PyPI
- **Task attempted:** Install pytest so the backend test suite could be run.
- **Steps taken:** Ran `python -m pip install pytest` in the restricted environment, then retried after requesting network-enabled approval.
- **Expected:** pip downloads pytest from PyPI.
- **Actual:** The restricted attempt failed DNS resolution for `pypi.org`; the approved retry installed pytest successfully.
- **Severity:** minor
- **Workaround:** Retry the package install with approved network access.
- **Suggestion:** Provide a configured package mirror or a documented offline dependency cache for restricted environments.

Live Gemini behavior has not been exercised because this environment has no configured API key.
