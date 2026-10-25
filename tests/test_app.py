from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_app_demo_and_validation_lab():
    app=AppTest.from_file(str(ROOT / "app.py"),default_timeout=30).run()
    assert not app.exception
    next(b for b in app.button if b.label == "Run four-supplier demo").click().run()
    assert not app.exception
    assert any(m.value == "NexaWorks" for m in app.metric)
    assert app.session_state.current_run["status"] == "completed"
    next(b for b in app.button if b.label == "Run validation case").click().run()
    assert not app.exception
    assert any("Rejected:" in e.value for e in app.error)


def test_live_mode_empty_input_is_explained():
    app=AppTest.from_file(str(ROOT / "app.py"),default_timeout=30).run()
    app.radio[0].set_value("Live Gemini evaluation").run()
    assert not app.exception
    next(c for c in app.checkbox if "Send extracted" in c.label).check().run()
    next(b for b in app.button if b.label == "Evaluate uploaded proposals").click().run()
    assert not app.exception
    assert any("API key" in e.value for e in app.error)
