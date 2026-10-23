from pathlib import Path
import time

from streamlit.testing.v1 import AppTest

from backend import assistant


APP = Path(__file__).resolve().parents[2] / "app.py"


def test_app_renders_idle_focus_panel_and_chat_response(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "startup-test.db"))
    monkeypatch.setattr(assistant, "new_chat", lambda: object())
    monkeypatch.setattr(
        assistant,
        "send",
        lambda *_args, **_kwargs: {"reply": "Allie response for the test.", "actions": []},
    )

    app = AppTest.from_file(str(APP), default_timeout=20)
    app.session_state["pomodoro_open"] = True
    app.run()

    assert not app.exception
    assert app.chat_input
    assert any("Focus hours" in str(widget.label) for widget in app.number_input)

    app.chat_input[0].set_value("Help me plan my study time").run()

    assert not app.exception
    assert any(
        "Allie response for the test." in str(widget.value)
        for widget in app.markdown
    )


def test_app_renders_running_focus_countdown(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "running-timer-test.db"))
    monkeypatch.setattr(assistant, "new_chat", lambda: object())

    app = AppTest.from_file(str(APP), default_timeout=20)
    app.session_state["pomodoro_open"] = True
    app.session_state["pomodoro_mode"] = "focus"
    app.session_state["focus_deadline"] = time.time() + 120
    app.session_state["focus_remaining"] = 120
    app.run()

    assert not app.exception
    assert any(button.label == "Ⅱ pause" for button in app.button)
